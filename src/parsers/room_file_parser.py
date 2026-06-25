"""
Parser for room data files.

Expected file format — one room per line, comma-separated:
    room_id,building,capacity

Example:
    101,1,50
    102,1,30
    201,2,80

Rules enforced during parsing:
  - Each line must have exactly three fields.
  - capacity must be a positive integer (validated by Room.__post_init__).
  - Duplicate (building, room_id) pairs within the same file are rejected.
  - Blank lines and lines starting with '#' are silently skipped.
"""

from src.parsers.file_parser import IFileParser
from src.models.room import Room


class RoomFileParser(IFileParser):
    """Reads a room data file and returns a list of validated Room objects."""

    def parse(self, filepath: str) -> list[Room]:
        rooms: list[Room] = []
        # Track (building, room_id) pairs seen so far to detect duplicates.
        seen: set[tuple[str, str]] = set()

        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line_number, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()

            # Skip blank lines and comment lines.
            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 3:
                raise ValueError(
                    f"Line {line_number}: expected 3 comma-separated fields "
                    f"(room_id, building, capacity), got {len(parts)}: '{line}'"
                )

            room_id, building, capacity_str = parts

            if not room_id:
                raise ValueError(f"Line {line_number}: room_id must not be empty.")
            if not building:
                raise ValueError(f"Line {line_number}: building must not be empty.")

            try:
                capacity = int(capacity_str)
            except ValueError:
                raise ValueError(
                    f"Line {line_number}: capacity must be an integer, got '{capacity_str}'."
                )

            # Room.__post_init__ enforces capacity > 0; let it raise naturally.
            room = Room(room_id, building, capacity)

            key = (building, room_id)
            if key in seen:
                raise ValueError(
                    f"Line {line_number}: duplicate room — "
                    f"(building={building!r}, room_id={room_id!r}) already defined."
                )
            seen.add(key)
            rooms.append(room)

        return rooms
