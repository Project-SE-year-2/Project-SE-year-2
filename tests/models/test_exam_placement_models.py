from datetime import date

from src.models.enums import TimeSlot
from src.models.exam_block import ExamBlock
from src.models.exam_placement import ExamPlacement
from src.models.room import Room


# Test that ExamBlock stores a date and time slot.
def test_exam_block_creation():
    block = ExamBlock(
        date=date(2026, 7, 1),
        time_slot=TimeSlot.MORNING,
    )

    assert block.date == date(2026, 7, 1)
    assert block.time_slot == TimeSlot.MORNING


# Test that date-only placement keeps backward-compatible values.
def test_date_only_exam_placement():
    placement = ExamPlacement.date_only(date(2026, 7, 1))

    assert placement.date == date(2026, 7, 1)
    assert placement.time_slot is None
    assert placement.rooms == ()
    assert placement.total_capacity == 0
    assert placement.is_room_based is False


# Test that room-based placement stores time slot and rooms.
def test_room_based_exam_placement():
    room = Room(room_id="101", building="4", capacity=80)

    placement = ExamPlacement.with_rooms(
        exam_date=date(2026, 7, 1),
        time_slot=TimeSlot.AFTERNOON,
        rooms=(room,),
    )

    assert placement.date == date(2026, 7, 1)
    assert placement.time_slot == TimeSlot.AFTERNOON
    assert placement.rooms == (room,)
    assert placement.is_room_based is True


# Test that total_capacity sums all assigned room capacities.
def test_total_capacity_multiple_rooms():
    room1 = Room(room_id="101", building="4", capacity=80)
    room2 = Room(room_id="102", building="4", capacity=50)

    placement = ExamPlacement.with_rooms(
        exam_date=date(2026, 7, 1),
        time_slot=TimeSlot.MORNING,
        rooms=(room1, room2),
    )

    assert placement.total_capacity == 130


# Test that total_capacity is zero when no rooms are assigned.
def test_total_capacity_without_rooms():
    placement = ExamPlacement.date_only(date(2026, 7, 1))

    assert placement.total_capacity == 0