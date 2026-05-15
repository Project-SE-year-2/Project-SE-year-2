from datetime import date
from src.course import Course
from src.i_collision_validator import ICollisionValidator
from src.constraint_index import ConstraintIndex


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
        # Same date — check whether the two courses share any obligatory group
        for group_courses in self._index.obligatoryGroups().values():
            if courseA in group_courses and courseB in group_courses:
                return False
        return True
