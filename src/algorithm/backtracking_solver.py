from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.algorithm.i_collision_validator import ICollisionValidator
from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.course_ordering_heuristic import CourseOrderingHeuristic
from src.algorithm.forward_checker import ForwardChecker


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

    def solve_stream(
        self,
        courses: list[Course],
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
    ):
        """
        Generator that yields valid exam schedules one at a time.
        Supports pause and resume via Python's native generator protocol.
        Each yielded schedule is a copy (never the mutable partial object).
        """
        partial = ExamSchedule(period)
        ordered = self._heuristic.orderByMostConstrained(courses, period)
        # 'yield from' delegates the generation to the recursive backtrack_stream
        # This allows yielding results one by one up to the caller
        yield from self._backtrack_stream(
            ordered, partial, period, constraint_validator
        )

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

    def _backtrack_stream(
        self,
        remaining: list[Course],
        partial: ExamSchedule,
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
    ):
        """
        Recursive generator that yields valid schedules one at a time.
        Yields a copy of partial on each solution, never the mutable partial itself.
        """
        # Base case - solution found
        if not remaining:
            # Yield a copy of the partial state to ensure external callers 
            # don't see modifications during backtracking
            yield partial.copy()
            return

        course = remaining[0]
        rest = remaining[1:]

        for exam_date in period.getAvailableDates():
            if constraint_validator.canAssign(course, exam_date, partial):
                partial.assign(course, exam_date)
                if self._forward_checker.hasViableAssignment(rest, partial, period):
                    # 'yield from' pauses this execution and yields results from 
                    # the recursive calls as they are found
                    yield from self._backtrack_stream(
                        rest, partial, period, constraint_validator
                    )
                partial.unassign(course)
