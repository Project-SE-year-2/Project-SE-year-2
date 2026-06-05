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
    ):
        self._validator = validator
        self._catalog = catalog
        self._index = index

        collision_validator = BasicVersionValidator(index)
        heuristic = CourseOrderingHeuristic(index)
        forward_checker = ForwardChecker(validator)

        self._solver = BacktrackingSolver(collision_validator, heuristic, forward_checker)
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

        worker_count = max_workers or min(32, len(scheduling_tasks))
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

    def solve_to_disk(self, period: ExamPeriod, courses_dict: dict, writer) -> int:
        """Solve one period with solve_stream() and write every BATCH_SIZE schedules
        directly to disk - at most one batch is in RAM at any moment.

        Returns the total number of valid schedules found.
        """
        pid = f"{period.semester.value}_{period.moed.value}"
        courses = list(courses_dict.keys())
        # Handle the edge case where no courses exist for this period
        if not courses:
            writer.update_manifest(pid, 0)
            return 0

        batch: list = []
        total = 0
        # Process solutions using a generator to keep memory consumption low
        for sched in self._solver.solve_stream(courses, period, self._validator):
            batch.append(sched)
            total += 1
            # Flush the batch to disk once it reaches the defined capacity
            if len(batch) >= BATCH_SIZE:
                writer.write_batch(pid, batch)
                # Clear the batch from RAM to allow garbage collection
                batch = []
        
        # Persist any remaining schedules that didn't fill the last batch
        if batch:
            writer.write_batch(pid, batch)
        return total

    def _orderCourses(self, courses, period: ExamPeriod) -> list:
        heuristic = CourseOrderingHeuristic(self._index)
        return heuristic.orderByMostConstrained(courses, period)
