from math import comb

from models.exam_period import ExamPeriod
from models.exam_schedule import ExamSchedule
from algorithm.constraint_validator import ConstraintValidator
from algorithm.exam_period_catalog import ExamPeriodCatalog
from algorithm.constraint_index import ConstraintIndex
from algorithm.basic_version_validator import BasicVersionValidator
from algorithm.course_ordering_heuristic import CourseOrderingHeuristic
from algorithm.forward_checker import ForwardChecker
from algorithm.backtracking_solver import BacktrackingSolver
from algorithm.schedule_combiner import ScheduleCombiner


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
        all_sub_results: list[list[ExamSchedule]] = []
        metadata: dict[ExamPeriod, dict] = {}

        for period, courses_dict in scheduling_tasks.items():
            courses = list(courses_dict.keys())
            n_days = len(period.getAvailableDates())
            n_courses = len(courses)

            theoretical = comb(n_days, n_courses) * n_courses if n_courses > 0 else 0

            period_results = self._solver.solve(courses, period, self._validator) if courses else []

            all_sub_results.append(period_results)
            metadata[period] = {
                "valid_count": len(period_results),
                "theoretical_count": theoretical,
                "courses": courses,
                "available_days": n_days,
            }

        combined = self._combiner.combineSubResults(all_sub_results)
        # Requirement 2.3.3: sort the schedules list by date order
        # (FALL Aleph -> FALL Bet -> SPRING Aleph ...)
        combined.sort(key=lambda s: s.sort_key)
        return combined, metadata

    def _orderCourses(self, courses, period: ExamPeriod) -> list:
        heuristic = CourseOrderingHeuristic(self._index)
        return heuristic.orderByMostConstrained(courses, period)
