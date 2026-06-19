from abc import ABC, abstractmethod
from src.models.exam_schedule import ExamSchedule


class IConstraint(ABC):
    """
    Interface for post-generation schedule filters.

    Each concrete constraint receives a fully-built ExamSchedule and decides
    whether it satisfies a specific scheduling rule.  Constraints are applied
    after the backtracking solver finishes — they never influence the search
    itself, only the final result set that is written to scores.db.
    """

    @abstractmethod
    def is_satisfied(self, schedule: ExamSchedule) -> bool:
        """Return True if the schedule passes this constraint, False otherwise."""
