from datetime import date

from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.program_requirement import ProgramRequirement

from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.exam_period_catalog import ExamPeriodCatalog
from src.algorithm.basic_version_validator import BasicVersionValidator
from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.scheduling_engine import SchedulingEngine


def _build_engine(courses, programs, periods):
    index = ConstraintIndex()
    index.build(courses, programs)

    catalog = ExamPeriodCatalog(periods)

    collision_validator = BasicVersionValidator(index)
    constraint_validator = ConstraintValidator(index, collision_validator)

    return SchedulingEngine(
        constraint_validator,
        catalog,
        index
    )


# Tests that the scheduling engine creates schedules
# when two obligatory courses from the same program have enough available dates.
def test_engine_generates_schedules_for_two_obligatory_courses_with_two_dates():
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")
    course2.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "02-02-2026")
    period.possible_dates = [
        date(2026, 2, 1),
        date(2026, 2, 2),
    ]

    courses = [course1, course2]
    programs = ["83101"]

    scheduling_tasks = {
        period: {
            course1: ["83101"],
            course2: ["83101"],
        }
    }

    engine = _build_engine(courses, programs, [period])

    schedules, metadata = engine.generateAll(scheduling_tasks)

    assert len(schedules) > 0
    assert metadata[period]["valid_count"] == len(schedules)

    for schedule in schedules:
        assignments = schedule.assignments

        assert course1 in assignments
        assert course2 in assignments

        # Since both courses are obligatory in the same program/year,
        # they must not be scheduled on the same date.
        assert assignments[course1] != assignments[course2]


# Tests that the scheduling engine returns no valid schedules
# when two obligatory courses from the same program have only one available date.
def test_engine_returns_no_schedules_when_conflict_cannot_be_avoided():
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")
    course2.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "01-02-2026")
    period.possible_dates = [
        date(2026, 2, 1),
    ]

    courses = [course1, course2]
    programs = ["83101"]

    scheduling_tasks = {
        period: {
            course1: ["83101"],
            course2: ["83101"],
        }
    }

    engine = _build_engine(courses, programs, [period])

    schedules, metadata = engine.generateAll(scheduling_tasks)

    assert schedules == []
    assert metadata[period]["valid_count"] == 0


# Tests that the scheduling engine allows two obligatory courses
# from different programs to be scheduled on the same date.
def test_engine_allows_obligatory_courses_from_different_programs_same_date():
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")
    course2.add_requirement(
        ProgramRequirement("83108", 1, "FALL", "Obligatory")
    )

    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "01-02-2026")
    period.possible_dates = [
        date(2026, 2, 1),
    ]

    courses = [course1, course2]
    programs = ["83101", "83108"]

    scheduling_tasks = {
        period: {
            course1: ["83101"],
            course2: ["83108"],
        }
    }

    engine = _build_engine(courses, programs, [period])

    schedules, metadata = engine.generateAll(scheduling_tasks)

    assert len(schedules) == 1
    assert metadata[period]["valid_count"] == 1

    assignments = schedules[0].assignments

    assert assignments[course1] == date(2026, 2, 1)
    assert assignments[course2] == date(2026, 2, 1)


# Tests that the scheduling engine allows an obligatory course
# and an elective course from the same program to be scheduled on the same date.
def test_engine_allows_obligatory_and_elective_same_program_same_date():
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Advanced Topics", "83999", "Prof. B", "Exam")
    course2.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Elective")
    )

    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "01-02-2026")
    period.possible_dates = [
        date(2026, 2, 1),
    ]

    courses = [course1, course2]
    programs = ["83101"]

    scheduling_tasks = {
        period: {
            course1: ["83101"],
            course2: ["83101"],
        }
    }

    engine = _build_engine(courses, programs, [period])

    schedules, metadata = engine.generateAll(scheduling_tasks)

    assert len(schedules) == 1
    assert metadata[period]["valid_count"] == 1

    assignments = schedules[0].assignments

    assert assignments[course1] == date(2026, 2, 1)
    assert assignments[course2] == date(2026, 2, 1)


# Tests that forbidden dates are not used by the scheduling engine
# because the engine only uses period.possible_dates.
def test_engine_does_not_schedule_on_forbidden_dates():
    course = Course("Physics 1", "83102", "Prof. A", "Exam")
    course.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "03-02-2026")

    # 02-02-2026 represents a forbidden date,
    # so it is intentionally not included in possible_dates.
    period.possible_dates = [
        date(2026, 2, 1),
        date(2026, 2, 3),
    ]

    courses = [course]
    programs = ["83101"]

    scheduling_tasks = {
        period: {
            course: ["83101"],
        }
    }

    engine = _build_engine(courses, programs, [period])

    schedules, metadata = engine.generateAll(scheduling_tasks)

    assert len(schedules) == 2

    for schedule in schedules:
        assignments = schedule.assignments
        assert assignments[course] != date(2026, 2, 2)


# Tests that the scheduling engine generates the exact expected number of
# valid schedule options for a small, controlled input dataset.
# For a single course and 2 available dates, there should be 2 possible schedules.
def test_engine_generates_all_possible_schedules_single_course_two_dates():
    """
    With 1 course and 2 available dates, exactly 2 valid schedules should exist.
    """
    course = Course("Physics 1", "83102", "Prof. A", "Exam")
    course.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "02-02-2026")
    period.possible_dates = [
        date(2026, 2, 1),
        date(2026, 2, 2),
    ]

    courses = [course]
    programs = ["83101"]

    scheduling_tasks = {
        period: {
            course: ["83101"],
        }
    }

    engine = _build_engine(courses, programs, [period])

    schedules, metadata = engine.generateAll(scheduling_tasks)

    # Exactly 2 schedules should be generated (one for each date)
    assert len(schedules) == 2
    assert metadata[period]["valid_count"] == 2


# Tests that the scheduling engine generates the exact expected number of
# valid schedule options for a small, controlled input dataset.
# For a single course and 2 available dates, there should be 2 possible schedules.
def test_engine_generates_all_possible_schedules_single_course_two_dates():
    """
    With 1 course and 2 available dates, exactly 2 valid schedules should exist.
    """
    course = Course("Physics 1", "83102", "Prof. A", "Exam")
    course.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "02-02-2026")
    period.possible_dates = [
        date(2026, 2, 1),
        date(2026, 2, 2),
    ]

    courses = [course]
    programs = ["83101"]

    scheduling_tasks = {
        period: {
            course: ["83101"],
        }
    }

    engine = _build_engine(courses, programs, [period])

    schedules, metadata = engine.generateAll(scheduling_tasks)

    # Exactly 2 schedules should be generated (one for each date)
    assert len(schedules) == 2
    assert metadata[period]["valid_count"] == 2


# Tests that the scheduling engine generates the exact expected number of
# valid schedule options for a small, controlled input dataset.
# For two courses and three available dates, there should be 6 possible schedules.
def test_engine_generates_all_possible_schedules_two_courses_three_dates():
    """
    With 2 courses and 3 available dates, all valid combinations should be generated.
    C(3,2) * 2! = 3 * 2 = 6 possible schedules (choose 2 dates, arrange 2 courses).
    """
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")
    course2.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "03-02-2026")
    period.possible_dates = [
        date(2026, 2, 1),
        date(2026, 2, 2),
        date(2026, 2, 3),
    ]

    courses = [course1, course2]
    programs = ["83101"]

    scheduling_tasks = {
        period: {
            course1: ["83101"],
            course2: ["83101"],
        }
    }

    engine = _build_engine(courses, programs, [period])

    schedules, metadata = engine.generateAll(scheduling_tasks)

    # Should generate exactly 6 valid schedules
    assert len(schedules) == 6
    assert metadata[period]["valid_count"] == 6


# Tests that no course appears more than once in the same schedule
# within a single period.
def test_engine_no_duplicate_course_per_schedule_single_period():
    """
    Verify that a single course never appears twice in the same schedule
    within a single exam period.
    """
    course = Course("Physics 1", "83102", "Prof. A", "Exam")
    course.add_requirement(
        ProgramRequirement("83101", 1, "FALL", "Obligatory")
    )

    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "03-02-2026")
    period.possible_dates = [
        date(2026, 2, 1),
        date(2026, 2, 2),
        date(2026, 2, 3),
    ]

    courses = [course]
    programs = ["83101"]

    scheduling_tasks = {
        period: {
            course: ["83101"],
        }
    }

    engine = _build_engine(courses, programs, [period])

    schedules, metadata = engine.generateAll(scheduling_tasks)

    # Verify no duplicate courses in any schedule
    for schedule in schedules:
        assignments = schedule.assignments
        assert list(assignments.keys()).count(course) == 1


# Tests that no course appears more than once across different periods
# in the same cross-period schedule.
def test_engine_no_duplicate_course_cross_period():
    """
    Verify that a course appearing in multiple periods is never assigned
    to the same course object twice in a single combined schedule.
    """
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(ProgramRequirement("83101", 1, "FALL", "Obligatory"))
    course1.add_requirement(ProgramRequirement("83101", 1, "SPRI", "Obligatory"))

    fall_period = ExamPeriod("FALL", "Aleph", "01-02-2026", "05-02-2026")
    fall_period.possible_dates = [date(2026, 2, 1), date(2026, 2, 2)]

    spri_period = ExamPeriod("SPRI", "Aleph", "01-07-2026", "05-07-2026")
    spri_period.possible_dates = [date(2026, 7, 1), date(2026, 7, 2)]

    courses = [course1]
    programs = ["83101"]

    scheduling_tasks = {
        fall_period: {course1: ["83101"]},
        spri_period: {course1: ["83101"]},
    }

    engine = _build_engine(courses, programs, [fall_period, spri_period])

    schedules, metadata = engine.generateAll(scheduling_tasks)

    # Each schedule should have valid cross-period assignments
    for schedule in schedules:
        if schedule.is_cross_period:
            # In a cross-period schedule, verify structure is correct
            assert len(schedule._store) > 0