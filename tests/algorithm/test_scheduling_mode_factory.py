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


def test_room_allocator_rejects_duplicate_physical_rooms():
    """
    Two Room objects with the same (building, room_id) represent the same
    physical room.  RoomAllocator.__init__ must raise ValueError rather than
    silently treating them as two separate rooms.
    """
    with pytest.raises(ValueError, match="Duplicate physical room"):
        RoomAllocator([Room("101", "1", 30), Room("101", "1", 50)])


def test_room_allocator_accepts_same_room_id_in_different_buildings():
    """room_id '101' in building '1' and '2' are distinct physical rooms."""
    allocator = RoomAllocator([Room("101", "1", 30), Room("101", "2", 30)])
    assert allocator.total_capacity == 60


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


def test_room_domain_returns_exam_blocks():
    """
    RoomSchedulingDomainProvider must return ExamBlock objects (date + time_slot).
    Room allocation is deferred to RoomPlacementFactory — not the domain provider.
    """
    from src.models.exam_block import ExamBlock

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
    assert all(isinstance(c, ExamBlock) for c in candidates)
    assert candidates[0].date == date(2026, 1, 1)
    assert candidates[0].time_slot in set(TimeSlot)


def test_room_allocator_does_not_reuse_same_room_in_same_slot():
    """
    After a room is assigned to one course in a given date+slot, RoomAllocator
    must not allocate the same room to a second course in the same slot.
    """
    from src.models.exam_block import ExamBlock
    from src.models.enums import TimeSlot

    room = Room("101", "1", 30)
    allocator = RoomAllocator([room])
    course = _course(students=10)
    period = _period()
    partial = ExamSchedule(period)

    # Use RoomPlacementFactory (which owns the allocator) to create the first placement.
    components = SchedulingModeFactory.create(
        ConstraintSettings(room_scheduling_enabled=True),
        [room],
    )
    block = ExamBlock(period.possible_dates[0], TimeSlot.MORNING)
    placement = components.placement_factory.create(block, course, partial)
    partial.assign(course, placement)

    assert placement.rooms == (room,)
    # The same room must be unavailable for a second course in the same slot.
    assert allocator.allocate(
        _course("C2", 10),
        period.possible_dates[0],
        TimeSlot.MORNING,
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
    """
    Greedy fallback runs when no single building has enough capacity.
    Rooms are in two different buildings (40 + 40 = 80 >= 70).
    The sliding window only considers same-building windows, so neither
    building alone is sufficient and the greedy path must be taken.
    """
    rooms = [
        Room("101", "1", 40),   # building 1 — alone: 40 < 70
        Room("101", "2", 40),   # building 2 — alone: 40 < 70
    ]
    allocator = RoomAllocator(rooms)
    period = _period()

    allocated = allocator.allocate(
        _course(students=70),
        period.possible_dates[0],
        TimeSlot.MORNING,
        ExamSchedule(period),
    )

    # Cross-building combination covers 80 >= 70.
    assert allocated is not None
    assert sum(r.capacity for r in allocated) >= 70
    buildings = {r.building for r in allocated}
    assert buildings == {"1", "2"}  # must have used rooms from both buildings


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


def test_room_model_rejects_zero_capacity():
    """Room.__post_init__ enforces capacity > 0, so FeasibilityChecker never sees a zero-capacity room."""
    with pytest.raises(ValueError, match="positive integer"):
        Room("101", "1", 0)


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


# ---------------------------------------------------------------------------
# Sliding-window allocation strategy
# ---------------------------------------------------------------------------

def test_sliding_window_only_considers_same_building_windows():
    """
    When a same-building window exists, the sliding window must not pick a
    cross-building window even if both satisfy capacity.
    Only the greedy fallback is allowed to combine rooms across buildings.
    """
    # Building "1" has 60 capacity (enough for 55).
    # Building "2" has 30 capacity (not enough alone).
    # Cross-building window [b1-102, b2-101] = 30+30 = 60, but spans 2 buildings.
    rooms = [
        Room("101", "1", 30),
        Room("102", "1", 30),
        Room("101", "2", 30),
    ]
    allocator = RoomAllocator(rooms)
    period = _period()

    allocated = allocator.allocate(
        _course(students=55),
        period.possible_dates[0],
        TimeSlot.MORNING,
        ExamSchedule(period),
    )

    # Must be solved by [b1-101, b1-102], not by any cross-building window.
    assert allocated is not None
    assert all(r.building == "1" for r in allocated)


def test_sliding_window_picks_tightest_window_among_candidates():
    """
    When multiple contiguous windows of the same size satisfy capacity,
    the one with the lowest unused capacity must be returned.
    """
    rooms = [
        Room("101", "1", 40),
        Room("102", "1", 60),  # this single room is tighter (unused=10)
        Room("103", "1", 80),  # this single room wastes more (unused=30)
    ]
    allocator = RoomAllocator(rooms)
    period = _period()

    allocated = allocator.allocate(
        _course(students=50),
        period.possible_dates[0],
        TimeSlot.MORNING,
        ExamSchedule(period),
    )

    # Room("102","1",60) is the tightest fit (unused=10) vs Room("103","1",80) (unused=30).
    assert allocated == (Room("102", "1", 60),)


def test_sliding_window_uses_fewest_rooms_first():
    """
    A single room that covers capacity must be chosen over a two-room window,
    even when the two-room window is contiguous and has less unused capacity.
    Fewest-rooms priority outranks tightest-fit.
    """
    rooms = [
        Room("101", "1", 30),
        Room("102", "1", 30),
        Room("103", "1", 70),
    ]
    allocator = RoomAllocator(rooms)
    period = _period()

    allocated = allocator.allocate(
        _course(students=60),
        period.possible_dates[0],
        TimeSlot.MORNING,
        ExamSchedule(period),
    )

    # Room("103","1",70) is the only single-room solution (unused=10).
    # The two-room window [101+102]=60 has unused=0 but requires two rooms,
    # so size=1 beats size=2 regardless of unused capacity.
    assert len(allocated) == 1
    assert allocated[0].room_id == "103"


# ---------------------------------------------------------------------------
# Occupancy check: (building, room_id) identity, not object equality
# ---------------------------------------------------------------------------

def test_occupancy_check_blocks_same_physical_room_different_object():
    """
    A Room object with the same (building, room_id) but a *different* capacity
    must still be treated as the same physical room and block re-allocation.

    This tests the fix from `room in placement.rooms` (which uses full object
    equality including capacity) to comparing by (building, room_id) only.
    """
    from src.models.exam_placement import ExamPlacement

    room_original = Room("101", "1", 50)
    # Same physical room, different capacity value — was NOT equal under old code.
    room_different_capacity = Room("101", "1", 999)

    allocator = RoomAllocator([room_original])
    period = _period()
    partial = ExamSchedule(period)

    # Manually place the same physical room (represented by a different object).
    placement = ExamPlacement(
        period.possible_dates[0],
        TimeSlot.MORNING,
        (room_different_capacity,),
    )
    partial.assign(_course("C1", 10), placement)

    # The allocator must recognise the room as occupied despite the object difference.
    result = allocator.allocate(
        _course("C2", 10),
        period.possible_dates[0],
        TimeSlot.MORNING,
        partial,
    )
    assert result is None


# ---------------------------------------------------------------------------
# Stable room identity — _room_identity helper (Task 2)
# ---------------------------------------------------------------------------

def test_same_room_id_different_capacity_treated_as_same_physical_room():
    """
    Room("101", "1", 30) and Room("101", "1", 50) share (building, room_id)
    and must therefore be treated as the same physical room by the allocator.
    Allocating one must block allocation of the other in the same slot.
    """
    from src.models.exam_placement import ExamPlacement

    room_30 = Room("101", "1", 30)
    room_50 = Room("101", "1", 50)  # different capacity, same physical room

    allocator = RoomAllocator([room_30])
    period = _period()
    partial = ExamSchedule(period)

    # Place room_50 (different object, same identity) in the schedule.
    placement = ExamPlacement(period.possible_dates[0], TimeSlot.MORNING, (room_50,))
    partial.assign(_course("C1", 10), placement)

    # room_30 must be blocked because its identity matches room_50.
    result = allocator.allocate(
        _course("C2", 10),
        period.possible_dates[0],
        TimeSlot.MORNING,
        partial,
    )
    assert result is None


def test_same_room_id_different_building_treated_as_different_physical_rooms():
    """
    Room("101", "1", 30) and Room("101", "2", 30) differ in building and must
    therefore be treated as distinct physical rooms.  Occupying one must NOT
    block allocation of the other in the same slot.
    """
    from src.models.exam_placement import ExamPlacement

    room_b1 = Room("101", "1", 30)
    room_b2 = Room("101", "2", 30)

    allocator = RoomAllocator([room_b1, room_b2])
    period = _period()
    partial = ExamSchedule(period)

    # Place room_b1 in the morning slot.
    placement = ExamPlacement(period.possible_dates[0], TimeSlot.MORNING, (room_b1,))
    partial.assign(_course("C1", 10), placement)

    # room_b2 (different building) must still be available.
    result = allocator.allocate(
        _course("C2", 10),
        period.possible_dates[0],
        TimeSlot.MORNING,
        partial,
    )
    assert result == (room_b2,)


def test_allocator_and_room_and_slot_constraint_agree_on_room_conflict():
    """
    RoomAllocator and RoomAndSlotConstraint must use the same room-identity
    logic.  A room assigned by the allocator must be flagged as a conflict by
    the constraint when a second exam tries to use it in the same slot.
    """
    from src.algorithm.constraints.room_and_slot_constraint import RoomAndSlotConstraint
    from src.models.exam_block import ExamBlock
    from src.models.exam_placement import ExamPlacement

    room = Room("101", "1", 50)
    period = _period()
    partial = ExamSchedule(period)
    constraint = RoomAndSlotConstraint()

    # First exam: allocated by the allocator.
    components = SchedulingModeFactory.create(
        ConstraintSettings(room_scheduling_enabled=True),
        [room],
    )
    block = ExamBlock(period.possible_dates[0], TimeSlot.MORNING)
    placement1 = components.placement_factory.create(block, _course("C1", 10), partial)
    partial.assign(_course("C1", 10), placement1)

    # Constraint is satisfied with one exam.
    assert constraint.is_satisfied(partial) is True

    # Second exam: manually insert the same room in the same slot.
    placement2 = ExamPlacement(period.possible_dates[0], TimeSlot.MORNING, (room,))
    partial.assign(_course("C2", 10), placement2)

    # Both allocator (no room available) and constraint (conflict) agree.
    assert constraint.is_satisfied(partial) is False
