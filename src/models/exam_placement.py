from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from src.models.enums import TimeSlot
from src.models.room import Room


@dataclass(frozen=True, slots=True)
class ExamPlacement:
    """
    Represents the final placement of one exam.

    Date-only mode:
        date=<exam date>
        time_slot=None
        rooms=()

    Room-scheduling mode:
        date=<exam date>
        time_slot=<TimeSlot>
        rooms=(Room(...), ...)
    """

    date: date
    time_slot: TimeSlot | None = None
    rooms: tuple[Room, ...] = field(default_factory=tuple)

    @classmethod
    def date_only(cls, exam_date: date) -> "ExamPlacement":
        """Create a backward-compatible date-only placement."""
        return cls(
            date=exam_date,
            time_slot=None,
            rooms=(),
        )

    @classmethod
    def with_rooms(
        cls,
        exam_date: date,
        time_slot: TimeSlot,
        rooms: tuple[Room, ...],
    ) -> "ExamPlacement":
        """Create a room-based placement."""
        return cls(
            date=exam_date,
            time_slot=time_slot,
            rooms=rooms,
        )

    @property
    def total_capacity(self) -> int:
        """Return the total capacity of all assigned rooms."""
        return sum(room.capacity for room in self.rooms)

    @property
    def is_room_based(self) -> bool:
        """Return True when this placement contains room scheduling data."""
        return self.time_slot is not None and len(self.rooms) > 0