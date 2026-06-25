"""Unit tests for RoomDistanceCalculator (EP-137)."""

from datetime import date

import pytest

from src.algorithm.scoring.room_distance_calculator import RoomDistanceCalculator
from src.models.exam_placement import ExamPlacement
from src.models.enums import TimeSlot
from src.models.room import Room
from src.models.exam_schedule import ExamSchedule
from tests.algorithm.constraint_helpers import make_obligatory_course, make_period, make_schedule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_room(room_id: str, building: str, capacity: int = 50) -> Room:
    return Room(room_id=room_id, building=building, capacity=capacity)


def make_room_schedule(*assignments: tuple) -> ExamSchedule:
    """Build an ExamSchedule from (course, ExamPlacement) pairs."""
    period = make_period()
    sched = ExamSchedule(period)
    for course, placement in assignments:
        sched.assign(course, placement)
    return sched


def room_placement(exam_date: date, *rooms: Room) -> ExamPlacement:
    return ExamPlacement.with_rooms(exam_date, TimeSlot.MORNING, tuple(rooms))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.fixture
def calc() -> RoomDistanceCalculator:
    return RoomDistanceCalculator()


def test_field_name(calc):
    """The calculator must register under the correct column name."""
    assert calc.field_name() == "avg_room_distance"


def test_empty_schedule_returns_zero(calc):
    """No placements at all - result must be the default 0.0."""
    sched = make_room_schedule()
    assert calc.compute(sched) == 0.0


def test_date_only_schedule_returns_zero(calc):
    """ScheduleScorer calls this calculator in date-only mode too;
    it must return 0.0 without crashing."""
    sched = make_schedule((make_obligatory_course("C1", "P1"), date(2026, 1, 10)))
    assert calc.compute(sched) == 0.0


def test_single_room_returns_one(calc):
    """One exam assigned to one room in one building - distance = 1."""
    c1 = make_obligatory_course("C1", "P1")
    sched = make_room_schedule((c1, room_placement(date(2026, 1, 10), make_room("A101", "A"))))
    assert calc.compute(sched) == 1.0


def test_multiple_rooms_same_building_returns_one(calc):
    """One exam assigned to three rooms, all in the same building - distance = 1."""
    c1 = make_obligatory_course("C1", "P1")
    sched = make_room_schedule((c1, room_placement(
        date(2026, 1, 10),
        make_room("A101", "A"),
        make_room("A102", "A"),
        make_room("A103", "A"),
    )))
    assert calc.compute(sched) == 1.0


def test_rooms_across_two_buildings_returns_two(calc):
    """One exam assigned to two rooms in two different buildings - distance = 2."""
    c1 = make_obligatory_course("C1", "P1")
    sched = make_room_schedule((c1, room_placement(
        date(2026, 1, 10),
        make_room("A101", "A"),
        make_room("B101", "B"),
    )))
    assert calc.compute(sched) == 2.0


def test_rooms_across_three_buildings_returns_three(calc):
    """One exam assigned to three rooms each in a different building - distance = 3."""
    c1 = make_obligatory_course("C1", "P1")
    sched = make_room_schedule((c1, room_placement(
        date(2026, 1, 10),
        make_room("A101", "A"),
        make_room("B101", "B"),
        make_room("C101", "C"),
    )))
    assert calc.compute(sched) == 3.0


def test_multiple_exams_all_single_building_returns_one(calc):
    """Two exams each assigned to rooms in one building - mean = 1.0."""
    c1 = make_obligatory_course("C1", "P1")
    c2 = make_obligatory_course("C2", "P1")
    sched = make_room_schedule(
        (c1, room_placement(date(2026, 1, 10), make_room("A101", "A"), make_room("A102", "A"))),
        (c2, room_placement(date(2026, 1, 11), make_room("B101", "B"), make_room("B102", "B"))),
    )
    assert calc.compute(sched) == 1.0


def test_average_across_multiple_exams(calc):
    """Two exams: Exam 1 assigned to 1 building, Exam 2 assigned to 2 buildings - mean = 1.5."""
    c1 = make_obligatory_course("C1", "P1")
    c2 = make_obligatory_course("C2", "P1")
    sched = make_room_schedule(
        (c1, room_placement(date(2026, 1, 10), make_room("A101", "A"))),
        (c2, room_placement(date(2026, 1, 11), make_room("A101", "A"), make_room("B101", "B"))),
    )
    assert calc.compute(sched) == 1.5
