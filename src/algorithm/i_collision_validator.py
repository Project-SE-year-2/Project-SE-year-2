from abc import ABC, abstractmethod
from datetime import date
from src.models.course import Course


class ICollisionValidator(ABC):
    """
    Interface for collision validation between two course-date assignments.
    Implementations decide what constitutes a scheduling conflict.
    """

    @abstractmethod
    def isValid(self, courseA: Course, dateA: date, courseB: Course, dateB: date) -> bool:
        """Returns True if assigning courseA to dateA and courseB to dateB is conflict-free."""
        pass
