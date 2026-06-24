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
    engine = SchedulingEngine(constraint_validator, catalog, index, constraint_settings=settings)

    assert engine._constraint_settings.room_scheduling_enabled is True