from datetime import date

from src.algorithm.constraints.constraint_checker import ConstraintChecker
from src.models.constraint_settings import ConstraintSettings
from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.models.program_requirement import ProgramRequirement
from src.models.enums import (
    Evaluation,
    Semester,
    Moed,
    ReqType,
)


# Create a course that belongs to a specific program and year.
def _make_course(
    name: str,
    course_id: str,
    program_id: str,
    year: int,
) -> Course:
    course = Course(
        name,
        course_id,
        "Prof. X",
        Evaluation.Exam,
    )

    course.add_requirement(
        ProgramRequirement(
            program_id,
            year,
            Semester.FALL,
            ReqType.Obligatory,
        )
    )

    return course


# Create a merged ExamSchedule from assignment tuples.
def _make_schedule(assignments: list[tuple]) -> ExamSchedule:
    schedules = []

    for period, course, exam_date in assignments:
        schedule = ExamSchedule(period)
        schedule.assign(course, exam_date)
        schedules.append(schedule)

    merged = schedules[0]

    for schedule in schedules[1:]:
        merged = merged.merge(schedule)

    return merged


FALL = ExamPeriod(
    Semester.FALL,
    Moed.Aleph,
    date(2026, 2, 1),
    date(2026, 3, 31),
)

PROGRAM = "83101"


# Verify that an empty registry always accepts schedules.
def test_is_valid_returns_true_when_no_constraints_enabled():
    settings = ConstraintSettings()

    checker = ConstraintChecker(settings)

    result = checker.is_valid(ExamSchedule(None))

    assert result is True


# Verify that enabled constraints are created during initialization.
def test_builds_enabled_constraints():
    settings = ConstraintSettings(
        all_gap_enabled=True,
        all_gap_k=5,
    )

    checker = ConstraintChecker(settings)

    assert len(checker._constraints) == 1


# Verify that a valid schedule passes all enabled constraints.
def test_is_valid_returns_true_for_valid_schedule():
    settings = ConstraintSettings(
        all_gap_enabled=True,
        all_gap_k=5,
    )

    checker = ConstraintChecker(settings)

    c1 = _make_course(
        "Physics",
        "101",
        PROGRAM,
        1,
    )

    c2 = _make_course(
        "Calculus",
        "102",
        PROGRAM,
        1,
    )

    schedule = _make_schedule([
        (FALL, c1, date(2026, 2, 1)),
        (FALL, c2, date(2026, 2, 10)),
    ])

    assert checker.is_valid(schedule) is True


# Verify that validation stops when a constraint fails.
def test_is_valid_returns_false_for_invalid_schedule():
    settings = ConstraintSettings(
        all_gap_enabled=True,
        all_gap_k=10,
    )

    checker = ConstraintChecker(settings)

    c1 = _make_course(
        "Physics",
        "101",
        PROGRAM,
        1,
    )

    c2 = _make_course(
        "Calculus",
        "102",
        PROGRAM,
        1,
    )

    schedule = _make_schedule([
        (FALL, c1, date(2026, 2, 1)),
        (FALL, c2, date(2026, 2, 5)),
    ])

    assert checker.is_valid(schedule) is False


# Verify that disabled constraints are not instantiated.
def test_disabled_constraint_is_not_created():
    settings = ConstraintSettings(
        all_gap_enabled=False,
        all_gap_k=5,
    )

    checker = ConstraintChecker(settings)

    assert len(checker._constraints) == 0

# Verify that all currently supported enabled constraints are created.
def test_builds_all_supported_enabled_constraints():
    settings = ConstraintSettings(
        all_gap_enabled=True,
        all_gap_k=5,
        elective_conflicts_enabled=True,
        elective_conflicts_k=1,
        spread_enabled=True,
        spread_k=10,
        daily_cap_enabled=True,
        daily_cap_k=3,
    )

    checker = ConstraintChecker(settings)

    assert len(checker._constraints) == 4

# Verify that DailyCapConstraint is applied by ConstraintChecker.
def test_is_valid_returns_false_when_daily_cap_fails():
    settings = ConstraintSettings(daily_cap_enabled=True, daily_cap_k=1)
    checker = ConstraintChecker(settings)

    c1 = _make_course("Physics", "101", PROGRAM, 1)
    c2 = _make_course("Calculus", "102", PROGRAM, 1)

    schedule = _make_schedule([
        (FALL, c1, date(2026, 2, 1)),
        (FALL, c2, date(2026, 2, 1)),
    ])

    assert checker.is_valid(schedule) is False