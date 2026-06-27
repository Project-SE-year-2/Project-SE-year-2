from datetime import date
from src.models.course import Course
from src.algorithm.i_collision_validator import ICollisionValidator
from src.algorithm.constraint_index import ConstraintIndex


class BasicVersionValidator(ICollisionValidator):
    """
    Basic collision rule: two courses collide if and only if they share
    an obligatory group AND are assigned to the same date.
    """

    def __init__(self, index: ConstraintIndex):
        self._index = index

    def isValid(self, courseA: Course, dateA: date, courseB: Course, dateB: date) -> bool:
        if dateA != dateB:
            return True
        # Same date — use O(1) lookup to check if the two courses share any obligatory group
        return not self._index.do_collide(courseA, courseB)
