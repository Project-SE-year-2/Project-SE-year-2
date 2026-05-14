import pytest
from datetime import date

from src.course import Course
from src.program_requirement import ProgramRequirement
from src.schedule_validator import validate_no_same_program_obligatory_conflict
from src.schedule_validator import validate_enough_dates_for_obligatory_courses


# Tests that the system raises a scheduling conflict error
# when two obligatory courses from the same program and same year
# are assigned to the same exam date.
def test_validate_conflict_for_two_obligatory_courses_same_program_same_day():

    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")

    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")

    course2.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    exam_date = date(2026, 2, 1)

    with pytest.raises(ValueError, match="same program"):
        validate_no_same_program_obligatory_conflict(
            course1,
            course2,
            exam_date
        )

# Tests that the system raises a clear error when there are
# more obligatory exams than available dates for a selected program.
def test_validate_not_enough_dates_for_obligatory_courses():

    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")
    course2.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    courses = [course1, course2]

    available_dates = [
        date(2026, 2, 1)
    ]

    with pytest.raises(ValueError, match="Cannot schedule exams for program 83101"):
        validate_enough_dates_for_obligatory_courses(
            courses,
            "83101",
            available_dates
        )

# Tests that two obligatory courses from different programs
# can be scheduled on the same date without raising an error.
def test_allows_obligatory_courses_from_different_programs_same_day():

    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")
    course2.add_requirement(
        ProgramRequirement("83108", 1, "FALL", "Obligatory")
    )

    exam_date = date(2026, 2, 1)

    validate_no_same_program_obligatory_conflict(
        course1,
        course2,
        exam_date
    )


# Tests that an obligatory course and an elective course
# from the same program can be scheduled on the same date
# without raising an error.
def test_allows_obligatory_and_elective_from_same_program_same_day():

    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Advanced Topics", "83999", "Prof. B", "Exam")
    course2.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Elective")
    )

    exam_date = date(2026, 2, 1)

    validate_no_same_program_obligatory_conflict(
        course1,
        course2,
        exam_date
    )        