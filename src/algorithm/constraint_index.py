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

    def obligatoryGroups(self) -> dict[tuple, list[Course]]:
        return self._obligatory_groups

    def groupKeyFor(self, course: Course) -> tuple | None:
        for req in course.requirements:
            if req.is_obligatory() and req.program_id in self._selected_programs:
                return (req.program_id, req.year, req.semester)
        return None

    def examCoursesInPrograms(self) -> list[Course]:
        return self._exam_courses
