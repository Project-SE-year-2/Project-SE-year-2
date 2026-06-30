from src.models.course import Course
from src.models.enums import Evaluation, ReqType

class ConstraintIndex:
    """
    Pre-computes and indexes all obligatory course groups.
    A group key is (program_id, year, semester) — all Obligatory courses
    sharing a key cannot be scheduled on the same exam date.

    Also pre-computes two additional pair sets used by ManualMoveValidator:
      _mandatory_gap_pairs - obligatory courses sharing the same (program_id, year)
                             (mirrors MandatoryGapConstraint grouping, no semester)
      _all_gap_pairs       - all courses sharing the same (program_id, year)
                             (mirrors AllGapConstraint grouping)
    """

    def __init__(self):
        self._obligatory_groups: dict[tuple, list[Course]] = {}
        self._exam_courses: list[Course] = []
        self._selected_programs: list[str] = []
        self._collision_set: set[tuple[str, str]] = set()
        self._mandatory_gap_pairs: set[tuple[str, str]] = set()
        self._all_gap_pairs: set[tuple[str, str]] = set()

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

        # Precompute the O(1) collision matrix (program_id, year, semester)
        self._collision_set.clear()
        for group_courses in self._obligatory_groups.values():
            n = len(group_courses)
            for i in range(n):
                for j in range(i + 1, n):
                    c1_id = group_courses[i].course_id
                    c2_id = group_courses[j].course_id
                    self._collision_set.add(tuple(sorted([c1_id, c2_id])))

        # Precompute mandatory-gap pairs: obligatory courses sharing (program_id, year)
        # Mirrors MandatoryGapConstraint._group_by_cohort - no semester dimension.
        self._mandatory_gap_pairs.clear()
        mand_cohorts: dict[tuple, list[str]] = {}
        for course in self._exam_courses:
            for req in course.requirements:
                if req.req_type == ReqType.Obligatory and req.program_id in self._selected_programs:
                    key = (req.program_id, req.year)
                    mand_cohorts.setdefault(key, [])
                    if course.course_id not in mand_cohorts[key]:
                        mand_cohorts[key].append(course.course_id)
        for ids in mand_cohorts.values():
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    self._mandatory_gap_pairs.add(tuple(sorted([ids[i], ids[j]])))

        # Precompute all-gap pairs: any courses sharing (program_id, year)
        # Mirrors AllGapConstraint._group_by_cohort - all req types included.
        self._all_gap_pairs.clear()
        all_cohorts: dict[tuple, list[str]] = {}
        for course in self._exam_courses:
            for req in course.requirements:
                if req.program_id in self._selected_programs:
                    key = (req.program_id, req.year)
                    all_cohorts.setdefault(key, [])
                    if course.course_id not in all_cohorts[key]:
                        all_cohorts[key].append(course.course_id)
        for ids in all_cohorts.values():
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    self._all_gap_pairs.add(tuple(sorted([ids[i], ids[j]])))

    def obligatoryGroups(self) -> dict[tuple, list[Course]]:
        return self._obligatory_groups

    def do_collide(self, courseA: Course, courseB: Course) -> bool:
        """O(1) lookup to check if two courses share an obligatory group."""
        return tuple(sorted([courseA.course_id, courseB.course_id])) in self._collision_set

    def do_collide_by_id(self, id_a: str, id_b: str) -> bool:
        """O(1) collision check using course ID strings instead of Course objects."""
        return tuple(sorted([id_a, id_b])) in self._collision_set

    def need_mandatory_gap(self, id_a: str, id_b: str) -> bool:
        """True if the two courses must respect the mandatory-gap constraint."""
        return tuple(sorted([id_a, id_b])) in self._mandatory_gap_pairs

    def need_all_gap(self, id_a: str, id_b: str) -> bool:
        """True if the two courses must respect the all-gap constraint."""
        return tuple(sorted([id_a, id_b])) in self._all_gap_pairs

    def groupKeyFor(self, course: Course) -> tuple | None:
        for req in course.requirements:
            if req.is_obligatory() and req.program_id in self._selected_programs:
                return (req.program_id, req.year, req.semester)
        return None

    def examCoursesInPrograms(self) -> list[Course]:
        return self._exam_courses