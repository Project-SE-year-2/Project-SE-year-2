from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.algorithm.constraint_index import ConstraintIndex


class CourseOrderingHeuristic:
    """
    Orders courses by the Most-Constrained-Variable heuristic:
    courses that share obligatory groups with the most other courses
    are placed first, enabling earlier pruning in backtracking.
    """

    def __init__(self, index: ConstraintIndex):
        self._index = index

    def orderByMostConstrained(self, courses: list[Course], period: ExamPeriod) -> list[Course]:
        def constraint_count(course: Course) -> int:
            count = 0
            for group_courses in self._index.obligatoryGroups().values():
                if course in group_courses:
                    # Each other course in the same group is a potential conflict
                    count += len(group_courses) - 1
            return count

        return sorted(courses, key=constraint_count, reverse=True)
