from datetime import date

from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.program_requirement import ProgramRequirement

from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.exam_period_catalog import ExamPeriodCatalog
from src.algorithm.basic_version_validator import BasicVersionValidator
from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.scheduling_engine import SchedulingEngine
from src.models.enums import Evaluation, Semester, Moed, ReqType
from src.models.constraint_settings import ConstraintSettings
from src.models.exam_placement import ExamPlacement
from src.models.room import Room


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
    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)
    course1.add_requirement(
        ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory)
    )

    course2 = Course("Calculus 1", "83112", "Prof. B", Evaluation.Exam)
    course2.add_requirement(
        ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory)
    )

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 2))
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
    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)
    course1.add_requirement(
        ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory)
    )

    course2 = Course("Calculus 1", "83112", "Prof. B", Evaluation.Exam)
    course2.add_requirement(
        ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory)
    )

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 1))
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


# Tests that ConstraintSettings (including room_scheduling_enabled) is stored on the engine
def test_engine_receives_and_stores_constraint_settings():
    index = ConstraintIndex()
    index.build([], [])
    catalog = ExamPeriodCatalog([])
    collision_validator = BasicVersionValidator(index)
    constraint_validator = ConstraintValidator(index, collision_validator)

    settings = ConstraintSettings(room_scheduling_enabled=True)
    engine = SchedulingEngine(
        constraint_validator,
        catalog,
        index,
        constraint_settings=settings,
        rooms=[Room("101", "1", 30)],
    )

    assert engine._constraint_settings.room_scheduling_enabled is True


def test_engine_room_mode_requires_room_data():
    index = ConstraintIndex()
    index.build([], [])
    catalog = ExamPeriodCatalog([])
    collision_validator = BasicVersionValidator(index)
    constraint_validator = ConstraintValidator(index, collision_validator)

    settings = ConstraintSettings(room_scheduling_enabled=True)

    try:
        SchedulingEngine(constraint_validator, catalog, index, constraint_settings=settings)
    except ValueError as exc:
        assert "no room data" in str(exc)
    else:
        raise AssertionError("Room scheduling should fail when no room data is provided.")


def test_engine_room_mode_generates_room_placements():
    course = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam, num_students=20)
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 1))
    period.possible_dates = [date(2026, 2, 1)]

    index = ConstraintIndex()
    index.build([course], ["83101"])
    catalog = ExamPeriodCatalog([period])
    collision_validator = BasicVersionValidator(index)
    constraint_validator = ConstraintValidator(index, collision_validator)

    engine = SchedulingEngine(
        constraint_validator,
        catalog,
        index,
        constraint_settings=ConstraintSettings(room_scheduling_enabled=True),
        rooms=[Room("101", "1", 30)],
    )

    schedules, metadata = engine.generateAll({period: {course: ["83101"]}})

    assert metadata[period]["valid_count"] == len(schedules)
    assert len(schedules) == 3
    for schedule in schedules:
        placement = schedule.placements[course]
        assert isinstance(placement, ExamPlacement)
        assert placement.date == date(2026, 2, 1)
        assert placement.time_slot is not None
        assert placement.rooms == (Room("101", "1", 30),)
