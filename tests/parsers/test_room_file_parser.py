"""
Tests for RoomFileParser.

Verified behaviours:
  - Valid files produce correctly populated Room objects.
  - Lines with wrong field count raise ValueError.
  - Non-integer and zero/negative capacity values raise ValueError.
  - Missing room_id or building fields raise ValueError.
  - Duplicate (building, room_id) pairs within the same file raise ValueError.
  - Blank lines and comment lines (starting with '#') are silently skipped.
"""

import pytest

from src.parsers.room_file_parser import RoomFileParser
from src.models.room import Room


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_file(tmp_path, content: str) -> str:
    """Write content to a temporary file and return its path as a string."""
    path = tmp_path / "rooms.txt"
    path.write_text(content, encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------------------
# Valid input
# ---------------------------------------------------------------------------

def test_single_room_parsed_correctly(tmp_path):
    path = _write_file(tmp_path, "101,1,50\n")
    rooms = RoomFileParser().parse(path)

    assert len(rooms) == 1
    assert rooms[0].room_id == "101"
    assert rooms[0].building == "1"
    assert rooms[0].capacity == 50


def test_multiple_rooms_all_parsed(tmp_path):
    content = "101,1,50\n102,1,30\n201,2,80\n"
    path = _write_file(tmp_path, content)
    rooms = RoomFileParser().parse(path)

    assert len(rooms) == 3
    assert {r.room_id for r in rooms} == {"101", "102", "201"}


def test_returns_room_objects(tmp_path):
    path = _write_file(tmp_path, "A1,BuildingX,100\n")
    rooms = RoomFileParser().parse(path)

    assert all(isinstance(r, Room) for r in rooms)


def test_same_room_id_in_different_buildings_is_allowed(tmp_path):
    """room_id '101' in building '1' and building '2' are distinct physical rooms."""
    content = "101,1,50\n101,2,60\n"
    path = _write_file(tmp_path, content)
    rooms = RoomFileParser().parse(path)

    assert len(rooms) == 2
    buildings = {r.building for r in rooms}
    assert buildings == {"1", "2"}


def test_whitespace_around_fields_is_stripped(tmp_path):
    path = _write_file(tmp_path, "  101 , 1 , 50 \n")
    rooms = RoomFileParser().parse(path)

    assert rooms[0].room_id == "101"
    assert rooms[0].building == "1"
    assert rooms[0].capacity == 50


def test_blank_lines_are_skipped(tmp_path):
    content = "\n101,1,50\n\n102,1,30\n\n"
    path = _write_file(tmp_path, content)
    rooms = RoomFileParser().parse(path)

    assert len(rooms) == 2


def test_comment_lines_are_skipped(tmp_path):
    content = "# This is a header\n101,1,50\n# another comment\n102,1,30\n"
    path = _write_file(tmp_path, content)
    rooms = RoomFileParser().parse(path)

    assert len(rooms) == 2


def test_empty_file_returns_empty_list(tmp_path):
    path = _write_file(tmp_path, "")
    rooms = RoomFileParser().parse(path)

    assert rooms == []


def test_file_with_only_comments_returns_empty_list(tmp_path):
    path = _write_file(tmp_path, "# just a comment\n# another\n")
    rooms = RoomFileParser().parse(path)

    assert rooms == []


# ---------------------------------------------------------------------------
# Invalid capacity
# ---------------------------------------------------------------------------

def test_non_integer_capacity_raises(tmp_path):
    path = _write_file(tmp_path, "101,1,fifty\n")
    with pytest.raises(ValueError, match="capacity"):
        RoomFileParser().parse(path)


def test_float_capacity_raises(tmp_path):
    path = _write_file(tmp_path, "101,1,3.5\n")
    with pytest.raises(ValueError, match="capacity"):
        RoomFileParser().parse(path)


def test_zero_capacity_raises(tmp_path):
    """Room.__post_init__ enforces capacity > 0."""
    path = _write_file(tmp_path, "101,1,0\n")
    with pytest.raises(ValueError):
        RoomFileParser().parse(path)


def test_negative_capacity_raises(tmp_path):
    path = _write_file(tmp_path, "101,1,-10\n")
    with pytest.raises(ValueError):
        RoomFileParser().parse(path)


# ---------------------------------------------------------------------------
# Missing fields
# ---------------------------------------------------------------------------

def test_too_few_fields_raises(tmp_path):
    path = _write_file(tmp_path, "101,1\n")
    with pytest.raises(ValueError, match="3 comma-separated fields"):
        RoomFileParser().parse(path)


def test_too_many_fields_raises(tmp_path):
    path = _write_file(tmp_path, "101,1,50,extra\n")
    with pytest.raises(ValueError, match="3 comma-separated fields"):
        RoomFileParser().parse(path)


def test_empty_room_id_raises(tmp_path):
    path = _write_file(tmp_path, ",1,50\n")
    with pytest.raises(ValueError, match="room_id"):
        RoomFileParser().parse(path)


def test_empty_building_raises(tmp_path):
    path = _write_file(tmp_path, "101,,50\n")
    with pytest.raises(ValueError, match="building"):
        RoomFileParser().parse(path)


# ---------------------------------------------------------------------------
# Duplicate rooms
# ---------------------------------------------------------------------------

def test_duplicate_room_same_building_raises(tmp_path):
    """The same (building, room_id) pair must be rejected."""
    content = "101,1,50\n101,1,30\n"
    path = _write_file(tmp_path, content)
    with pytest.raises(ValueError, match="duplicate room"):
        RoomFileParser().parse(path)


def test_duplicate_detected_regardless_of_capacity(tmp_path):
    """Duplicates are keyed by (building, room_id) only — capacity doesn't affect dedup."""
    content = "101,1,50\n101,1,50\n"
    path = _write_file(tmp_path, content)
    with pytest.raises(ValueError, match="duplicate room"):
        RoomFileParser().parse(path)
