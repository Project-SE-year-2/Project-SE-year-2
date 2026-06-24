from src.models.course import Course
from src.models.exam_schedule import ExamSchedule
from src.models.exam_period import ExamPeriod
from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.constraints.partial_constraint_checker import PartialConstraintChecker


class ForwardChecker:
    """
    Pruning optimisation: verifies that every unassigned course still has
    at least one valid available date given the current partial assignment.
    If any course has no viable date, the branch is pruned immediately.

    When a partial_checker is supplied (AllGap, DailyCap, etc.) each candidate
    date is also tested against those constraints before being counted as viable.
    """

    def __init__(self, validator: ConstraintValidator):
        self._validator = validator

    def hasViableAssignment(
        self,
        remaining: list[Course],
        partial: ExamSchedule,
        period: ExamPeriod,
        partial_checker: PartialConstraintChecker | None = None,
    ) -> bool:
        available_dates = period.getAvailableDates()
        for course in remaining:
            has_valid_date = False
            for d in available_dates:
                if not self._validator.canAssign(course, d, partial):
                    continue
                if partial_checker is not None:
                    partial.assign(course, d)
                    ok = partial_checker.is_valid_partial(partial)
                    partial.unassign(course)
                    if not ok:
                        continue
                has_valid_date = True
                break
            if not has_valid_date:
                return False
        return True
