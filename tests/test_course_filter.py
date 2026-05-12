import pytest

from src.course import Course, ProgramRequirement
from src.course_parser import filter_courses_for_scheduling


# Tests that an Exam course that belongs to a selected program
# is kept after filtering.
def test_filter_keeps_exam_course_that_belongs_to_selected_program():
    course = Course("Physics 1", "83102", "Prof. O. Some", "Exam")
    course.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )
    result = filter_courses_for_scheduling([course], ["83101"])

    assert result == [course]

# Tests that a Project course is removed even if
# it belongs to one of the selected programs.
def test_filter_removes_project_course_even_if_program_matches():
    course = Course("Software Project", "83533", "Dr. Terry Bell", "Project")
    course.add_requirement(
        ProgramRequirement("83108", 2, "SPRI", "Obligatory")
    )

    result = filter_courses_for_scheduling([course], ["83108"])

    assert result == []

# Tests that an Attendance course is removed even if
# it belongs to one of the selected programs.
def test_filter_removes_attendance_course_even_if_program_matches():
    course = Course("Seminar", "83999", "Dr. Example", "Attendance")
    course.add_requirement(
        ProgramRequirement("83101", 3, "FALL", "Elective")
    )

    result = filter_courses_for_scheduling([course], ["83101"])

    assert result == []

# Tests that an Exam course is removed if it does not
# belong to any of the selected programs.
def test_filter_removes_exam_course_if_program_does_not_match():
    course = Course("Calculus 1", "83112", "Dr. Erez Scheiner", "Exam")
    course.add_requirement(
        ProgramRequirement("83102", 1, "FALL", "Obligatory")
    )

    result = filter_courses_for_scheduling([course], ["83108"])

    assert result == []

# Tests that a course is kept if at least one of its
# program requirements matches a selected program.
def test_filter_keeps_course_if_at_least_one_program_matches():
    course = Course("Physics 1", "83102", "Prof. O. Some", "Exam")
    course.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )
    course.add_requirement(
        ProgramRequirement("83102", 1, "FALL", "Obligatory")
    )

    result = filter_courses_for_scheduling([course], ["83108", "83102"])

    assert result == [course]

# Tests that the function raises a ValueError
# when the selected programs list is empty.
def test_filter_raises_error_when_selected_programs_is_empty():
    course = Course("Physics 1", "83102", "Prof. O. Some", "Exam")
    course.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    with pytest.raises(ValueError):
        filter_courses_for_scheduling([course], [])