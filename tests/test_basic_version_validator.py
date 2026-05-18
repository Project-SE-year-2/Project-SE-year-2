from datetime import date

from src.models.course import Course
from src.models.program_requirement import ProgramRequirement
from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.basic_version_validator import BasicVersionValidator

# Helper that build for all our tests the BasicVersionValidator
# instead for each test 
def _build_validator(courses, selected_programs):
    index = ConstraintIndex()
    index.build(courses, selected_programs)
    return BasicVersionValidator(index)

# Tests that two obligatory courses from the same program,
# same year, and same semester cannot be scheduled on the same date.
def test_obligatory_courses_same_program_same_year_same_day_are_invalid():
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")
    course2.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    validator = _build_validator([course1, course2], ["83101"])

    assert validator.isValid(
        course1,
        date(2026, 2, 1),
        course2,
        date(2026, 2, 1),
    ) is False

# Tests that two obligatory courses from the same program
# are allowed if they are scheduled on different dates.
def test_obligatory_courses_same_program_different_days_are_valid():
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")
    course2.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    validator = _build_validator([course1, course2], ["83101"])

    assert validator.isValid(
        course1,
        date(2026, 2, 1),
        course2,
        date(2026, 2, 2),
    ) is True

# Tests that two obligatory courses from different programs
# can be scheduled on the same date.
def test_obligatory_courses_different_programs_same_day_are_valid():
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")
    course2.add_requirement(
        ProgramRequirement("83108", 1, "FALL", "Obligatory")
    )

    validator = _build_validator([course1, course2], ["83101", "83108"])

    assert validator.isValid(
        course1,
        date(2026, 2, 1),
        course2,
        date(2026, 2, 1),
    ) is True

# Tests that an obligatory course and an elective course
# from the same program can be scheduled on the same date.
def test_obligatory_and_elective_same_program_same_day_are_valid():
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Advanced Topics", "83999", "Prof. B", "Exam")
    course2.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Elective")
    )

    validator = _build_validator([course1, course2], ["83101"])

    assert validator.isValid(
        course1,
        date(2026, 2, 1),
        course2,
        date(2026, 2, 1),
    ) is True

# Tests that two obligatory courses from the same program
# but different years can be scheduled on the same date.
def test_obligatory_courses_same_program_different_years_same_day_are_valid():
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Advanced Physics", "83222", "Prof. B", "Exam")
    course2.add_requirement(
        ProgramRequirement("83101", 2, "FALL", "Obligatory")
    )

    validator = _build_validator([course1, course2], ["83101"])

    assert validator.isValid(
        course1,
        date(2026, 2, 1),
        course2,
        date(2026, 2, 1),
    ) is True
