from src.models.exam_schedule import ExamSchedule
from src.algorithm.constraints.i_partial_constraint import IPartialConstraint


class PartialConstraintChecker:
    """Runs all active partial constraints against a partial schedule."""

    def __init__(self, constraints: list[IPartialConstraint]) -> None:
        """Store the active partial constraints."""
        self._constraints = constraints

    def is_valid_partial(self, schedule: ExamSchedule) -> bool:
        """Return True only if every active partial constraint accepts the partial schedule."""
        return all(
            constraint.is_still_valid(schedule)
            for constraint in self._constraints
        )