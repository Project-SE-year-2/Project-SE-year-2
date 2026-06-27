from src.models.course import Course
from src.models.enums import Evaluation

class ConstraintIndex:
    """
    Pre-computes and indexes all obligatory course groups.
    A group key is (program_id, year, semester) — all Obligatory courses
    sharing a key cannot be scheduled on the same exam date.
    """

    def __init__(self):
        self._obligatory_groups: dict[tuple, list[Course]] = {}
        self._exam_courses: list[Course] = []
        self._selected_programs: list[str] = []
        self._collision_set: set[tuple[str, str]] = set()

    def build(self, courses: list[Course], programs: list[str]) -> None:
        self._selected_programs = list(programs)
        self._exam_courses = [c for c in courses if c.evaluation == Evaluation.Exam]
        self._obligatory_groups = {}

        for course in self._exam_courses:
            for req in course.requirements:
                if req.is_obligatory() and req.program_id in self._selected_programs:
                    key = (req.program_id, req.year, req.semester)
                    if key not in self._obligatory_groups:
                        self._obligatory_groups[key] = []
                    if course not in self._obligatory_groups[key]:
                        self._obligatory_groups[key].append(course)

        # Precompute the O(1) collision matrix
        self._collision_set.clear()
        for group_courses in self._obligatory_groups.values():
            n = len(group_courses)
            for i in range(n):
                for j in range(i + 1, n):
                    c1_id = group_courses[i].course_id
                    c2_id = group_courses[j].course_id
                    self._collision_set.add(tuple(sorted([c1_id, c2_id])))

    def obligatoryGroups(self) -> dict[tuple, list[Course]]:
        return self._obligatory_groups

    def do_collide(self, courseA: Course, courseB: Course) -> bool:
        """O(1) lookup to check if two courses share an obligatory group."""
        return tuple(sorted([courseA.course_id, courseB.course_id])) in self._collision_set

    def groupKeyFor(self, course: Course) -> tuple | None:
        for req in course.requirements:
            if req.is_obligatory() and req.program_id in self._selected_programs:
                return (req.program_id, req.year, req.semester)
        return None

    def examCoursesInPrograms(self) -> list[Course]:
        return self._exam_courses
