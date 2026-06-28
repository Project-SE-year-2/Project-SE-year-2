from datetime import date
from src.models.course import Course
from src.models.exam_schedule import ExamSchedule
from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.i_collision_validator import ICollisionValidator


class ConstraintValidator:
    """
    High-level validator used by the backtracking solver.
    Delegates collision detection to the injected ICollisionValidator.
    """

    def __init__(self, index: ConstraintIndex, collision_validator: ICollisionValidator):
        self._index = index
        self._collision_validator = collision_validator

    def canAssign(self, course: Course, exam_date: date, schedule: ExamSchedule) -> bool:
        """True if assigning course to exam_date causes no conflict with the partial schedule."""
        for assigned_course in schedule.get_courses_on_date(exam_date):
            if not self._collision_validator.isValid(course, exam_date, assigned_course, exam_date):
                return False
        return True

    def collides(self, c1: Course, c2: Course) -> bool:
        return self._shareObligatoryGroup(c1, c2)

    def _shareObligatoryGroup(self, c1: Course, c2: Course) -> bool:
        for group_courses in self._index.obligatoryGroups().values():
            if c1 in group_courses and c2 in group_courses:
                return True
        return False
