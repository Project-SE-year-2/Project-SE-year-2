from abc import ABC, abstractmethod

from src.models.exam_schedule import ExamSchedule


class IPartialConstraint(ABC):
    """Interface for constraints that can prune partial schedules during backtracking."""

    @abstractmethod
    def is_still_valid(self, schedule: ExamSchedule) -> bool:
        """Return True if the partial schedule can still become a valid final schedule."""