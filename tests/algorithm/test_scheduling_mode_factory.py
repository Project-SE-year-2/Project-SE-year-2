from datetime import date

import pytest

from src.algorithm.basic_version_validator import BasicVersionValidator
from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.scheduling_mode_factory import (
    DateOnlyDomainProvider,
    DateOnlyFeasibilityChecker,
    DateOnlyPlacementFactory,
    RoomAllocator,
    RoomPlacementFactory,
    RoomSchedulingFeasibilityChecker,
    RoomSchedulingDomainProvider,
    SchedulingModeFactory,
)
from src.models.constraint_settings import ConstraintSettings
from src.models.course import Course
from src.models.enums import Evaluation, Moed, Semester, TimeSlot
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.models.room import Room


def _validator() -> ConstraintValidator:
    index = ConstraintIndex()
    index.build([], [])
    collision_validator = BasicVersionValidator(index)
    return ConstraintValidator(index, collision_validator)


def _course(course_id: str = "C1", students: int = 20) -> Course:
    return Course(f"Course {course_id}", course_id, "Prof", Evaluation.Exam, students)


def _period() -> ExamPeriod:
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 1))
    period.possible_dates = [date(2026, 1, 1)]
    return period


def test_factory_date_only_mode_does_not_require_rooms():
    components = SchedulingModeFactory.create(ConstraintSettings(room_scheduling_enabled=False))

    assert isinstance(components.domain_provider, DateOnlyDomainProvider)
    assert isinstance(components.placement_factory, DateOnlyPlacementFactory)
    assert isinstance(components.feasibility_checker, DateOnlyFeasibilityChecker)
    assert components.room_allocator is None


def test_factory_room_mode_requires_room_data():
    with pytest.raises(ValueError, match="no room data"):
        SchedulingModeFactory.create(ConstraintSettings(room_scheduling_enabled=True))


def test_factory_room_mode_wires_room_components():
    rooms = [Room("101", "1", 30)]
    components = SchedulingModeFactory.create(
        ConstraintSettings(room_scheduling_enabled=True),
        rooms,
    )

    assert isinstance(components.domain_provider, RoomSchedulingDomainProvider)
    assert isinstance(components.placement_factory, RoomPlacementFactory)
    assert isinstance(components.feasibility_checker, RoomSchedulingFeasibilityChecker)
    assert isinstance(components.room_allocator, RoomAllocator)


def test_date_only_domain_returns_dates():
    components = SchedulingModeFactory.create(ConstraintSettings(room_scheduling_enabled=False))
    period = _period()
    candidates = components.domain_provider.candidates_for(
        _course(),
        ExamSchedule(period),
        period,
        _validator(),
    )

    assert candidates == [date(2026, 1, 1)]


def test_room_domain_returns_room_placements():
    rooms = [Room("101", "1", 30)]
    components = SchedulingModeFactory.create(
        ConstraintSettings(room_scheduling_enabled=True),
        rooms,
    )
    period = _period()

    candidates = components.domain_provider.candidates_for(
        _course(students=10),
        ExamSchedule(period),
        period,
        _validator(),
    )

    assert len(candidates) == len(TimeSlot)
    assert candidates[0].date == date(2026, 1, 1)
    assert candidates[0].time_slot in set(TimeSlot)
    assert candidates[0].rooms == (rooms[0],)


def test_room_allocator_does_not_reuse_same_room_in_same_slot():
    room = Room("101", "1", 30)
    allocator = RoomAllocator([room])
    course = _course(students=10)
    period = _period()
    partial = ExamSchedule(period)
    components = SchedulingModeFactory.create(
        ConstraintSettings(room_scheduling_enabled=True),
        [room],
    )
    placement = components.domain_provider.candidates_for(
        course, partial, period, _validator()
    )[0]
    partial.assign(course, placement)

    assert placement.rooms == (room,)
    assert allocator.allocate(
        _course("C2", 10),
        period.possible_dates[0],
        placement.time_slot,
        partial,
    ) is None


def test_room_allocator_prefers_smallest_single_room_that_fits():
    rooms = [
        Room("101", "1", 100),
        Room("102", "1", 30),
        Room("103", "1", 60),
    ]
    allocator = RoomAllocator(rooms)
    period = _period()

    allocated = allocator.allocate(
        _course(students=50),
        period.possible_dates[0],
        TimeSlot.MORNING,
        ExamSchedule(period),
    )

    assert allocated == (rooms[2],)


def test_room_allocator_uses_greedy_multi_room_fallback():
    rooms = [
        Room("101", "1", 40),
        Room("102", "1", 35),
        Room("103", "1", 20),
    ]
    allocator = RoomAllocator(rooms)
    period = _period()

    allocated = allocator.allocate(
        _course(students=70),
        period.possible_dates[0],
        TimeSlot.MORNING,
        ExamSchedule(period),
    )

    assert allocated == (rooms[0], rooms[1])


def test_room_allocator_rejects_missing_student_count():
    allocator = RoomAllocator([Room("101", "1", 30)])
    period = _period()

    allocated = allocator.allocate(
        _course(students=0),
        period.possible_dates[0],
        TimeSlot.MORNING,
        ExamSchedule(period),
    )

    assert allocated is None


def test_room_feasibility_rejects_missing_student_count():
    components = SchedulingModeFactory.create(
        ConstraintSettings(room_scheduling_enabled=True),
        [Room("101", "1", 30)],
    )

    is_valid, message = components.feasibility_checker.validate_courses([
        _course(students=0)
    ])

    assert is_valid is False
    assert "positive student count" in message


def test_room_feasibility_rejects_course_over_total_capacity():
    components = SchedulingModeFactory.create(
        ConstraintSettings(room_scheduling_enabled=True),
        [Room("101", "1", 30), Room("102", "1", 20)],
    )

    is_valid, message = components.feasibility_checker.validate_courses([
        _course(students=60)
    ])

    assert is_valid is False
    assert "total room capacity" in message
