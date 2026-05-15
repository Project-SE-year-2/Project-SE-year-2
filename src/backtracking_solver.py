from src.course import Course
from src.exam_period import ExamPeriod
from src.exam_schedule import ExamSchedule
from src.i_collision_validator import ICollisionValidator
from src.constraint_validator import ConstraintValidator
from src.course_ordering_heuristic import CourseOrderingHeuristic
from src.forward_checker import ForwardChecker


class BacktrackingSolver:
    """
    Enumerates ALL valid exam schedules for a single ExamPeriod via backtracking.
    Uses the Most-Constrained-Variable heuristic and forward-checking to prune
    the search tree early.
    """

    def __init__(
        self,
        validator: ICollisionValidator,
        heuristic: CourseOrderingHeuristic,
        forward_checker: ForwardChecker,
    ):
        self._validator = validator
        self._heuristic = heuristic
        self._forward_checker = forward_checker

    def solve(
        self,
        courses: list[Course],
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
    ) -> list[ExamSchedule]:
        results: list[ExamSchedule] = []
        partial = ExamSchedule(period)
        ordered = self._heuristic.orderByMostConstrained(courses, period)
        self._backtrack(ordered, partial, period, constraint_validator, results)
        return results

    def _backtrack(
        self,
        remaining: list[Course],
        partial: ExamSchedule,
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
        results: list[ExamSchedule],
    ) -> None:
        if not remaining:
            results.append(partial.copy())
            return

        course = remaining[0]
        rest = remaining[1:]

        for exam_date in period.getAvailableDates():
            if constraint_validator.canAssign(course, exam_date, partial):
                partial.assign(course, exam_date)
                if self._forward_checker.hasViableAssignment(rest, partial, period):
                    self._backtrack(rest, partial, period, constraint_validator, results)
                partial.unassign(course)
