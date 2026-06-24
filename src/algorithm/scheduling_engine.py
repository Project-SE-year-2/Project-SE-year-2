from concurrent.futures import ThreadPoolExecutor, as_completed
from math import comb

from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.exam_period_catalog import ExamPeriodCatalog
from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.basic_version_validator import BasicVersionValidator
from src.algorithm.course_ordering_heuristic import CourseOrderingHeuristic
from src.algorithm.forward_checker import ForwardChecker
from src.algorithm.backtracking_solver import BacktrackingSolver
from src.algorithm.schedule_combiner import ScheduleCombiner
from src.algorithm.generation_result import PeriodGenerationResult
from src.algorithm.period_results_writer import BATCH_SIZE
from src.models.constraint_settings import ConstraintSettings
from src.algorithm.constraints.partial_constraint_registry import PartialConstraintRegistry


class SchedulingEngine:
    """
    Orchestrates the full scheduling process.
    Receives the pre-partitioned scheduling tasks (from match_courses_to_periods),
    runs BacktrackingSolver on each ExamPeriod, then aggregates via ScheduleCombiner.

    The theoretical schedule count per period is:
        C(available_days, num_courses) * num_courses
    where C is the binomial coefficient.
    """

    def __init__(
        self,
        validator: ConstraintValidator,
        catalog: ExamPeriodCatalog,
        index: ConstraintIndex,
        constraint_settings: ConstraintSettings | None = None,
    ):
        self._validator = validator
        self._catalog = catalog
        self._index = index
        self._constraint_settings = constraint_settings

        collision_validator = BasicVersionValidator(index)
        heuristic = CourseOrderingHeuristic(index)
        forward_checker = ForwardChecker(validator)
        partial_constraint_checker = PartialConstraintRegistry.build(constraint_settings)

        self._solver = BacktrackingSolver(collision_validator, heuristic, forward_checker, partial_constraint_checker)
        self._combiner = ScheduleCombiner()

    def _solve_period(
        self,
        period: ExamPeriod,
        courses_dict: dict,
    ) -> PeriodGenerationResult:
        courses = list(courses_dict.keys())
        n_days = len(period.getAvailableDates())
        n_courses = len(courses)

        theoretical = comb(n_days, n_courses) * n_courses if n_courses > 0 else 0
        period_results = self._solver.solve(courses, period, self._validator) if courses else []

        return PeriodGenerationResult(
            period=period,
            schedules=period_results,
            metadata={
                "valid_count": len(period_results),
                "theoretical_count": theoretical,
                "courses": courses,
                "available_days": n_days,
            },
        )

    def iterPeriodResults(
        self,
        scheduling_tasks: dict[ExamPeriod, dict],
        max_workers: int | None = None,
    ):
        """Yield each solved period as soon as a worker finishes it."""
        if not scheduling_tasks:
            return

        worker_count = max_workers or 1
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {
                executor.submit(self._solve_period, period, courses_dict): period
                for period, courses_dict in scheduling_tasks.items()
            }

            for future in as_completed(future_map):
                yield future.result()

    def generateAll(
        self, scheduling_tasks: dict[ExamPeriod, dict]
    ) -> tuple[list[ExamSchedule], dict[ExamPeriod, dict]]:
        """
        Returns:
            - flat list of all valid ExamSchedule objects (one per valid assignment per period)
            - metadata dict: ExamPeriod -> {
                  'valid_count': int,
                  'theoretical_count': int,
                  'courses': list[Course],
                  'available_days': int,
              }
        """
        period_results_by_period: dict[ExamPeriod, PeriodGenerationResult] = {}

        for period_result in self.iterPeriodResults(scheduling_tasks):
            period_results_by_period[period_result.period] = period_result

        all_sub_results: list[list[ExamSchedule]] = []
        metadata: dict[ExamPeriod, dict] = {}

        for period in scheduling_tasks.keys():
            period_result = period_results_by_period[period]
            all_sub_results.append(period_result.schedules)
            metadata[period] = period_result.metadata

        combined = self._combiner.combineSubResults(all_sub_results)
        # Requirement 2.3.3: sort the schedules list by date order
        # (FALL Aleph -> FALL Bet -> SPRING Aleph ...)
        combined.sort(key=lambda s: s.sort_key)
        return combined, metadata

    def solve_to_disk(self, period: ExamPeriod, courses_dict: dict, writer, on_batch_written=None, constraint_checker=None, scorer=None, scores_db=None) -> int:
        """Solve one period with solve_stream() and write every BATCH_SIZE schedules
        directly to disk - at most one batch is in RAM at any moment.

        If constraint_checker is provided, each schedule is evaluated against all
        enabled advanced constraints before being accepted; failing schedules are
        silently discarded. Passing None disables filtering (default behaviour).

        If scorer and scores_db are provided, quality metrics are computed for every
        accepted schedule and persisted to scores.db so the UI can sort by them.

        Returns the total number of valid schedules written to disk.
        """
        pid = period.period_id
        # Clear stale results from any previous run before writing new ones.
        # Also ensures manifest stays at 0 when the solver finds no valid schedules.
        writer.clear_period(pid)
        if scores_db is not None:
            scores_db.clear_period(pid)

        courses = list(courses_dict.keys())
        if not courses:
            return 0

        batch: list = []
        score_rows: list = []  # (batch_number, index_in_batch, metrics)
        total = 0
        for sched in self._solver.solve_stream(courses, period, self._validator):
            if constraint_checker is not None and not constraint_checker.is_valid(sched):
                continue

            # Linear index determines (batch_number, index_in_batch) in PKL files
            linear = total
            batch.append(sched)
            if scorer is not None and scores_db is not None:
                score_rows.append((linear // BATCH_SIZE, linear % BATCH_SIZE, scorer.compute_scores(sched)))
            total += 1

            # Eagerly write the very first schedule to disk to unblock the UI instantly
            if total == 1:
                writer.write_batch(pid, batch)
                if score_rows:
                    scores_db.insert_batch(pid, score_rows)
                if on_batch_written:
                    on_batch_written()
                batch = []
                score_rows = []
            elif len(batch) >= BATCH_SIZE:
                writer.write_batch(pid, batch)
                if score_rows:
                    scores_db.insert_batch(pid, score_rows)
                if on_batch_written:
                    on_batch_written()
                batch = []
                score_rows = []

        if batch:
            writer.write_batch(pid, batch)
            if score_rows:
                scores_db.insert_batch(pid, score_rows)
            if on_batch_written:
                on_batch_written()
        return total

    def solve_all_to_disk_round_robin(self, tasks: dict, writer, on_first_batch_written=None) -> None:
        """
        Solves all periods using a round-robin approach. 
        Pulls BATCH_SIZE schedules from each period in a cycle so that all periods 
        have some results available almost immediately.
        """
        generators = {}
        for period, courses_dict in tasks.items():
            pid = period.period_id
            writer.clear_period(pid)
            courses = list(courses_dict.keys())
            if courses:
                generators[pid] = self._solver.solve_stream(courses, period, self._validator)
        
        active_pids = list(generators.keys())
        first_batch_sent = set()

        while active_pids:
            for pid in list(active_pids):
                gen = generators[pid]
                batch = []
                try:
                    for _ in range(BATCH_SIZE):
                        batch.append(next(gen))
                except StopIteration:
                    active_pids.remove(pid)
                    if batch:
                        writer.write_batch(pid, batch)
                        if pid not in first_batch_sent and on_first_batch_written:
                            on_first_batch_written(pid)
                            first_batch_sent.add(pid)
                    continue
                
                if batch:
                    writer.write_batch(pid, batch)
                    if pid not in first_batch_sent and on_first_batch_written:
                        on_first_batch_written(pid)
                        first_batch_sent.add(pid)

    def _orderCourses(self, courses, period: ExamPeriod) -> list:
        heuristic = CourseOrderingHeuristic(self._index)
        return heuristic.orderByMostConstrained(courses, period)
