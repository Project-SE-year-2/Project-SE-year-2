import pytest

from src.models.room import Room
from src.models.enums import TimeSlot


# --- Room tests ---

def test_room_creation():
    room = Room(room_id="02", building="4", capacity=30)
    assert room.room_id == "02"
    assert room.building == "4"
    assert room.capacity == 30


def test_room_creation_large_building():
    room = Room(room_id="03", building="11", capacity=120)
    assert room.building == "11"
    assert room.capacity == 120


def test_room_zero_capacity_rejected():
    with pytest.raises(ValueError):
        Room(room_id="01", building="4", capacity=0)


def test_room_negative_capacity_rejected():
    with pytest.raises(ValueError):
        Room(room_id="01", building="4", capacity=-5)


def test_room_capacity_one_is_valid():
    room = Room(room_id="01", building="2", capacity=1)
    assert room.capacity == 1


def test_room_float_capacity_rejected():
    with pytest.raises(ValueError):
        Room(room_id="01", building="4", capacity=1.5)


def test_room_bool_capacity_rejected():
    with pytest.raises(ValueError):
        Room(room_id="01", building="4", capacity=True)


def test_room_string_capacity_rejected():
    with pytest.raises(ValueError):
        Room(room_id="01", building="4", capacity="30")


# --- TimeSlot tests ---

def test_timeslot_values_exist():
    assert TimeSlot.MORNING is not None
    assert TimeSlot.AFTERNOON is not None
    assert TimeSlot.EVENING is not None


def test_timeslot_string_values():
    assert TimeSlot.MORNING.value == "MORNING"
    assert TimeSlot.AFTERNOON.value == "AFTERNOON"
    assert TimeSlot.EVENING.value == "EVENING"


def test_timeslot_lookup_by_value():
    assert TimeSlot("MORNING") == TimeSlot.MORNING
    assert TimeSlot("AFTERNOON") == TimeSlot.AFTERNOON
    assert TimeSlot("EVENING") == TimeSlot.EVENING