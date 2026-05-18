import pytest
from src.models.course import Course
from src.models.program_requirement import ProgramRequirement
from src.algorithm.constraint_index import ConstraintIndex
from src.models.enums import Evaluation, Semester, ReqType

def test_constraint_index_builds_obligatory_groups():
    """
    Tests that ConstraintIndex correctly builds conflict groups based on
    the (program_id, year, semester) key, ensuring that only Obligatory
    courses are grouped together while Elective courses are ignored.
    """
    course1 = Course(
        "Physics 1",
        "83102",
        "Prof. A",
        Evaluation.Exam
    )

    course1.add_requirement(
        ProgramRequirement(
            "83101",
            1,
            Semester.FALL,
            ReqType.Obligatory
        )
    )

    course2 = Course(
        "Calculus 1",
        "83112",
        "Prof. B",
        Evaluation.Exam
    )

    course2.add_requirement(
        ProgramRequirement(
            "83101",
            1,
            Semester.FALL,
            ReqType.Obligatory
        )
    )

    course3 = Course(
        "Elective 1",
        "83113",
        "Prof. C",
        Evaluation.Exam
    )

    course3.add_requirement(
        ProgramRequirement(
            "83101",
            1,
            Semester.FALL,
            ReqType.Elective
        )
    )

    index = ConstraintIndex()
    index.build([course1, course2, course3], ["83101"])

    groups = index.obligatoryGroups()

    key = ("83101", 1, Semester.FALL)

    assert key in groups
    assert course1 in groups[key]
    assert course2 in groups[key]

    # Elective courses should not be part of obligatory groups
    assert course3 not in groups[key]

def test_constraint_index_group_key_for():
    """
    Tests that groupKeyFor correctly extracts and formats the structural tuple key
    for a given valid course matching the selected programs.
    """
    course1 = Course(
        "Physics 1",
        "83102",
        "Prof. A",
        Evaluation.Exam
    )

    course1.add_requirement(
        ProgramRequirement(
            "83101",
            1,
            Semester.FALL,
            ReqType.Obligatory
        )
    )

    index = ConstraintIndex()
    index.build([course1], ["83101"])

    assert index.groupKeyFor(course1) == (
        "83101",
        1,
        Semester.FALL
    )

# Tests that a course belonging to two selected programs
# is inserted into both obligatory conflict groups.
def test_constraint_index_course_belonging_to_two_programs_added_to_both_groups():
    course = Course(
        "Shared Course",
        "100",
        "Prof. A",
        Evaluation.Exam
    )

    course.add_requirement(
        ProgramRequirement(
            "83101",
            1,
            Semester.FALL,
            ReqType.Obligatory
        )
    )

    course.add_requirement(
        ProgramRequirement(
            "83108",
            1,
            Semester.FALL,
            ReqType.Obligatory
        )
    )

    index = ConstraintIndex()
    index.build([course], ["83101", "83108"])

    groups = index.obligatoryGroups()

    key1 = ("83101", 1, Semester.FALL)
    key2 = ("83108", 1, Semester.FALL)

    assert key1 in groups
    assert key2 in groups

    assert course in groups[key1]
    assert course in groups[key2]


# Tests that examCoursesInPrograms returns only Exam courses
# and ignores Project or other non-exam courses.
def test_constraint_index_exam_courses_in_programs_ignores_non_exam_courses():
    exam_course = Course(
        "Physics 1",
        "83102",
        "Prof. A",
        Evaluation.Exam
    )

    exam_course.add_requirement(
        ProgramRequirement(
            "83101",
            1,
            Semester.FALL,
            ReqType.Obligatory
        )
    )

    project_course = Course(
        "Software Project",
        "83533",
        "Prof. B",
        Evaluation.Project
    )

    project_course.add_requirement(
        ProgramRequirement(
            "83101",
            1,
            Semester.FALL,
            ReqType.Obligatory
        )
    )

    index = ConstraintIndex()
    index.build([exam_course, project_course], ["83101"])

    exam_courses = index.examCoursesInPrograms()

    assert exam_course in exam_courses
    assert project_course not in exam_courses