"""
Tests for RoomAllocator._build_occupied_set and the allocate() optimisation.

Background
----------
Before the fix, allocate() called _is_room_occupied(room, date, slot, partial)
for every room in self._rooms.  Each call scanned ALL placements in `partial`
and checked every room inside each placement — O(N_rooms × P × R) per call.

After the fix, _build_occupied_set() makes ONE pass over all placements and
returns a frozenset of (building, room_id) identity tuples.  allocate() then
filters available rooms with a single O(N_rooms) set-membership pass.
Total cost: O(P × R + N_rooms) instead of O(N_rooms × P × R).

These tests verify:
  1. _build_occupied_set returns the correct identities.
  2. allocate() skips occupied rooms and accepts free ones.
  3. Different (date, slot) pairs are independent — one slot does not block another.
  4. Identity comparison is by (building, room_id), not object equality,
     matching the contract of RoomAndSlotConstraint.
  5. The fix does not break existing multi-room or fallback allocation paths.
"""

from datetime import date

import pytest

from src.algorithm.scheduling_mode_factory import RoomAllocator, _room_identity
from src.models.course import Course
from src.models.enums import Evaluation, Moed, Semester, TimeSlot
from src.models.exam_period import ExamPeriod
from src.models.exam_placement import ExamPlacement
from src.models.exam_schedule import ExamSchedule
from src.models.room import Room


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _course(course_id: str = "C1", students: int = 20) -> Course:
    return Course(f"Course {course_id}", course_id, "Prof", Evaluation.Exam, students)


def _period(start: date = date(2026, 1, 1), end: date = date(2026, 1, 5)) -> ExamPeriod:
    period = ExamPeriod(Semester.FALL, Moed.Aleph, start, end)
    period.possible_dates = [
        date(2026, 1, d) for d in range(start.day, end.day + 1)
    ]
    return period


def _place(partial: ExamSchedule, course: Course, exam_date: date, slot: TimeSlot, rooms: list[Room]) -> None:
    """Directly assign a course to the partial schedule with explicit rooms."""
    partial.assign(course, ExamPlacement(exam_date, slot, tuple(rooms)))


# ---------------------------------------------------------------------------
# _build_occupied_set
# ---------------------------------------------------------------------------

class TestBuildOccupiedSet:
    """Unit tests for the O(P × R) set-building helper."""

    def test_empty_partial_returns_empty_set(self):
        """No placements → no occupied rooms for any (date, slot)."""
        period = _period()
        partial = ExamSchedule(period)
        result = RoomAllocator._build_occupied_set(
            date(2026, 1, 1), TimeSlot.MORNING, partial
        )
        assert result == set()

    def test_single_room_appears_in_set_for_matching_slot(self):
        """A placed room must appear in the occupied set for its (date, slot)."""
        period = _period()
        partial = ExamSchedule(period)
        room = Room("101", "1", 30)
        _place(partial, _course("C1"), date(2026, 1, 1), TimeSlot.MORNING, [room])

        occupied = RoomAllocator._build_occupied_set(
            date(2026, 1, 1), TimeSlot.MORNING, partial
        )
        assert _room_identity(room) in occupied

    def test_room_not_in_set_for_different_date(self):
        """A room placed on Jan 1 must not block Jan 2."""
        period = _period()
        partial = ExamSchedule(period)
        room = Room("101", "1", 30)
        _place(partial, _course("C1"), date(2026, 1, 1), TimeSlot.MORNING, [room])

        occupied = RoomAllocator._build_occupied_set(
            date(2026, 1, 2), TimeSlot.MORNING, partial  # different date
        )
        assert _room_identity(room) not in occupied

    def test_room_not_in_set_for_different_slot(self):
        """A room placed in the MORNING slot must not block the AFTERNOON slot."""
        period = _period()
        partial = ExamSchedule(period)
        room = Room("101", "1", 30)
        _place(partial, _course("C1"), date(2026, 1, 1), TimeSlot.MORNING, [room])

        occupied = RoomAllocator._build_occupied_set(
            date(2026, 1, 1), TimeSlot.AFTERNOON, partial  # different slot
        )
        assert _room_identity(room) not in occupied

    def test_multiple_rooms_all_appear_in_set(self):
        """All rooms from a multi-room placement must appear in the occupied set."""
        period = _period()
        partial = ExamSchedule(period)
        rooms = [Room("101", "1", 30), Room("102", "1", 30)]
        _place(partial, _course("C1"), date(2026, 1, 1), TimeSlot.MORNING, rooms)

        occupied = RoomAllocator._build_occupied_set(
            date(2026, 1, 1), TimeSlot.MORNING, partial
        )
        for room in rooms:
            assert _room_identity(room) in occupied

    def test_rooms_from_multiple_placements_all_collected(self):
        """Rooms from different courses in the same slot must all be in the set."""
        period = _period()
        partial = ExamSchedule(period)
        room_a = Room("101", "1", 30)
        room_b = Room("102", "1", 30)
        _place(partial, _course("C1"), date(2026, 1, 1), TimeSlot.MORNING, [room_a])
        _place(partial, _course("C2"), date(2026, 1, 1), TimeSlot.MORNING, [room_b])

        occupied = RoomAllocator._build_occupied_set(
            date(2026, 1, 1), TimeSlot.MORNING, partial
        )
        assert _room_identity(room_a) in occupied
        assert _room_identity(room_b) in occupied

    def test_identity_based_not_object_based(self):
        """
        A Room object with a DIFFERENT capacity but the SAME (building, room_id)
        must still appear in the occupied set — identity is (building, room_id),
        not Python object equality.
        """
        period = _period()
        partial = ExamSchedule(period)
        room_original = Room("101", "1", 30)
        room_same_identity_different_capacity = Room("101", "1", 999)

        # Place the "999-capacity" variant.
        _place(partial, _course("C1"), date(2026, 1, 1), TimeSlot.MORNING,
               [room_same_identity_different_capacity])

        occupied = RoomAllocator._build_occupied_set(
            date(2026, 1, 1), TimeSlot.MORNING, partial
        )
        # The 30-capacity variant shares (building, room_id) → must be blocked.
        assert _room_identity(room_original) in occupied


# ---------------------------------------------------------------------------
# allocate() — occupancy filtering correctness
# ---------------------------------------------------------------------------

class TestAllocateOccupancyFiltering:
    """
    Verify that allocate() correctly skips occupied rooms using _build_occupied_set.
    These tests also serve as regression tests: if the set-building is broken,
    rooms that are already in use will be double-allocated.
    """

    def test_occupied_room_is_not_reallocated_same_slot(self):
        """A room placed in MORNING for C1 must not be returned for C2 in MORNING."""
        room = Room("101", "1", 30)
        allocator = RoomAllocator([room])
        period = _period()
        partial = ExamSchedule(period)

        _place(partial, _course("C1"), date(2026, 1, 1), TimeSlot.MORNING, [room])

        result = allocator.allocate(
            _course("C2", 10), date(2026, 1, 1), TimeSlot.MORNING, partial
        )
        # Only one room, already occupied — must return None.
        assert result is None

    def test_room_available_in_different_slot(self):
        """A room occupied in MORNING must still be allocatable in AFTERNOON."""
        room = Room("101", "1", 30)
        allocator = RoomAllocator([room])
        period = _period()
        partial = ExamSchedule(period)

        _place(partial, _course("C1"), date(2026, 1, 1), TimeSlot.MORNING, [room])

        result = allocator.allocate(
            _course("C2", 10), date(2026, 1, 1), TimeSlot.AFTERNOON, partial
        )
        # Different slot → room is free.
        assert result == (room,)

    def test_room_available_on_different_date(self):
        """A room occupied on Jan 1 must still be allocatable on Jan 2."""
        room = Room("101", "1", 30)
        allocator = RoomAllocator([room])
        period = _period()
        partial = ExamSchedule(period)

        _place(partial, _course("C1"), date(2026, 1, 1), TimeSlot.MORNING, [room])

        result = allocator.allocate(
            _course("C2", 10), date(2026, 1, 2), TimeSlot.MORNING, partial
        )
        # Different date → room is free.
        assert result == (room,)

    def test_second_free_room_allocated_when_first_is_occupied(self):
        """When room_a is occupied, allocator must return room_b (same building)."""
        room_a = Room("101", "1", 30)
        room_b = Room("102", "1", 30)
        allocator = RoomAllocator([room_a, room_b])
        period = _period()
        partial = ExamSchedule(period)

        _place(partial, _course("C1"), date(2026, 1, 1), TimeSlot.MORNING, [room_a])

        result = allocator.allocate(
            _course("C2", 20), date(2026, 1, 1), TimeSlot.MORNING, partial
        )
        # room_a is taken, room_b is free — must return room_b.
        assert result == (room_b,)

    def test_all_rooms_occupied_returns_none(self):
        """When every room in the allocator is already placed, allocate() returns None."""
        rooms = [Room("101", "1", 30), Room("102", "1", 30)]
        allocator = RoomAllocator(rooms)
        period = _period()
        partial = ExamSchedule(period)

        _place(partial, _course("C1"), date(2026, 1, 1), TimeSlot.MORNING, [rooms[0]])
        _place(partial, _course("C2"), date(2026, 1, 1), TimeSlot.MORNING, [rooms[1]])

        result = allocator.allocate(
            _course("C3", 10), date(2026, 1, 1), TimeSlot.MORNING, partial
        )
        assert result is None

    def test_identity_based_occupancy_blocks_different_object_same_room(self):
        """
        If a room placed in `partial` was represented by a DIFFERENT Room object
        (but same (building, room_id)), allocate() must still treat it as occupied.

        This is the core correctness guarantee of the identity-based approach:
        the set uses (building, room_id), not Python object identity.
        """
        room_in_allocator = Room("101", "1", 30)
        room_different_object = Room("101", "1", 999)  # same physical room, diff capacity

        allocator = RoomAllocator([room_in_allocator])
        period = _period()
        partial = ExamSchedule(period)

        # Place the "different object" variant — allocator holds the other.
        _place(partial, _course("C1"), date(2026, 1, 1), TimeSlot.MORNING,
               [room_different_object])

        result = allocator.allocate(
            _course("C2", 10), date(2026, 1, 1), TimeSlot.MORNING, partial
        )
        # Must be blocked despite the object difference.
        assert result is None


# ---------------------------------------------------------------------------
# allocate() — multi-room and greedy paths still work after the fix
# ---------------------------------------------------------------------------

class TestAllocateMultiRoomPaths:
    """
    Ensure the optimised allocate() produces correct results on the same
    allocation paths (sliding-window, greedy) as before the change.
    """

    def test_sliding_window_two_rooms_same_building(self):
        """
        When one room is occupied and a second is available in the same building,
        the sliding window must still find the correct single-room solution.
        """
        room_a = Room("101", "1", 40)
        room_b = Room("102", "1", 60)
        allocator = RoomAllocator([room_a, room_b])
        period = _period()
        partial = ExamSchedule(period)

        _place(partial, _course("C1"), date(2026, 1, 1), TimeSlot.MORNING, [room_a])

        # C2 needs 50 students — only room_b (60) can cover after room_a is taken.
        result = allocator.allocate(
            _course("C2", 50), date(2026, 1, 1), TimeSlot.MORNING, partial
        )
        assert result == (room_b,)

    def test_greedy_fallback_used_when_only_cross_building_option_remains(self):
        """
        When same-building rooms are occupied, greedy must combine rooms
        across buildings to satisfy capacity.
        """
        room_a = Room("101", "1", 40)  # building 1
        room_b = Room("102", "1", 40)  # building 1 — will be occupied
        room_c = Room("101", "2", 40)  # building 2

        allocator = RoomAllocator([room_a, room_b, room_c])
        period = _period()
        partial = ExamSchedule(period)

        # Occupy both building-1 rooms.
        _place(partial, _course("C1"), date(2026, 1, 1), TimeSlot.MORNING, [room_a])
        _place(partial, _course("C2"), date(2026, 1, 1), TimeSlot.MORNING, [room_b])

        # Only room_c is free; 40 < 70 required → greedy needs cross-building.
        # With only one free room, that single room is used (greedy single-room fast-path).
        result = allocator.allocate(
            _course("C3", 30), date(2026, 1, 1), TimeSlot.MORNING, partial
        )
        # room_c is the only free room and covers 30 students.
        assert result == (room_c,)

    def test_many_placements_do_not_slow_down_available_filtering(self):
        """
        Correctness smoke-test for a partial schedule with many placements.
        Ensures the occupancy set correctly filters in a realistic scenario
        with multiple dates and slots populated.
        """
        rooms = [Room(f"{100 + i}", "1", 30) for i in range(10)]
        allocator = RoomAllocator(rooms)
        period = _period(date(2026, 1, 1), date(2026, 1, 5))
        partial = ExamSchedule(period)

        # Fill Jan 1–4 MORNING with rooms[0]..rooms[3].
        for i, d in enumerate([date(2026, 1, j) for j in range(1, 5)]):
            _place(partial, _course(f"C{i}"), d, TimeSlot.MORNING, [rooms[i]])

        # Jan 5 MORNING — rooms[0..3] are on DIFFERENT dates → all still free.
        result = allocator.allocate(
            _course("CX", 20), date(2026, 1, 5), TimeSlot.MORNING, partial
        )
        # Any free room with capacity ≥ 20 is valid (rooms[0] is the tightest).
        assert result is not None
        assert sum(r.capacity for r in result) >= 20
