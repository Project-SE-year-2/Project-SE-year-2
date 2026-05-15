from datetime import date

from src.models.course import Course
from src.models.exam_schedule import ExamSchedule
from src.models.program_requirement import ProgramRequirement
from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.basic_version_validator import BasicVersionValidator
from src.algorithm.constraint_validator import ConstraintValidator
from src.models.exam_period import ExamPeriod


def _build_constraint_validator(courses, selected_programs):
    index = ConstraintIndex()
    index.build(courses, selected_programs)

    collision_validator = BasicVersionValidator(index)

    return ConstraintValidator(index, collision_validator)


# Tests that returns False when assigning a course
# to a date with an already assigned obligatory course.
def test_can_assign_returns_false_for_same_program_obligatory_conflict():
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")
    course2.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "03-02-2026")
    schedule = ExamSchedule(period)
    schedule.assign(course1, date(2026, 2, 1))

    validator = _build_constraint_validator([course1, course2], ["83101"])

    assert validator.canAssign(course2, date(2026, 2, 1), schedule) is False


# Tests that returns True when two obligatory courses
# from the same program are assigned to different dates.
def test_can_assign_returns_true_for_same_program_different_dates():
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")
    course2.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "03-02-2026")
    schedule = ExamSchedule(period)
    schedule.assign(course1, date(2026, 2, 1))

    validator = _build_constraint_validator([course1, course2], ["83101"])

    assert validator.canAssign(course2, date(2026, 2, 2), schedule) is True


# Tests that the canAssign function returns True when two obligatory courses
# from different programs are assigned to the same date.
def test_can_assign_returns_true_for_different_programs_same_date():
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")
    course2.add_requirement(
        ProgramRequirement("83108", 1, "FALL", "Obligatory")
    )

    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "03-02-2026")
    schedule = ExamSchedule(period)
    schedule.assign(course1, date(2026, 2, 1))

    validator = _build_constraint_validator(
        [course1, course2],
        ["83101", "83108"]
    )

    assert validator.canAssign(course2, date(2026, 2, 1), schedule) is True


# Tests that the canAssign function returns True when an obligatory course
# and an elective course from the same program are assigned to the same date.
def test_can_assign_returns_true_for_obligatory_and_elective_same_program():
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Advanced Topics", "83999", "Prof. B", "Exam")
    course2.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Elective")
    )

    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "03-02-2026")
    schedule = ExamSchedule(period)
    schedule.assign(course1, date(2026, 2, 1))

    validator = _build_constraint_validator([course1, course2], ["83101"])

    assert validator.canAssign(course2, date(2026, 2, 1), schedule) is True


# Tests that the function collides returns True for two obligatory courses
# that belong to the same program, year, and semester.
def test_collides_returns_true_for_same_obligatory_group():
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")
    course2.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    validator = _build_constraint_validator([course1, course2], ["83101"])

    assert validator.collides(course1, course2) is True


# Tests that the collides function returns False for courses that do not
# belong to the same obligatory conflict group.
def test_collides_returns_false_for_non_conflicting_courses():
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Advanced Topics", "83999", "Prof. B", "Exam")
    course2.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Elective")
    )

    validator = _build_constraint_validator([course1, course2], ["83101"])

    assert validator.collides(course1, course2) is False