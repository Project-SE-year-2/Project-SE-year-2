from src.course import Course
from src.exam_schedule import ExamSchedule
from src.exam_period import ExamPeriod
from src.constraint_validator import ConstraintValidator


class ForwardChecker:
    """
    Pruning optimisation: verifies that every unassigned course still has
    at least one valid available date given the current partial assignment.
    If any course has no viable date, the branch is pruned immediately.
    """

    def __init__(self, validator: ConstraintValidator):
        self._validator = validator

    def hasViableAssignment(
        self, remaining: list[Course], partial: ExamSchedule, period: ExamPeriod
    ) -> bool:
        available_dates = period.getAvailableDates()
        for course in remaining:
            has_valid_date = any(
                self._validator.canAssign(course, d, partial) for d in available_dates
            )
            if not has_valid_date:
                return False
        return True
