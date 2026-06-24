from __future__ import annotations

from dataclasses import dataclass
from datetime import date as DateType

from src.models.enums import TimeSlot
from src.models.room import Room


@dataclass(frozen=True)
class ExamPlacement:
    """
    Represents the full placement of one course exam.

    Date-only schedules use only the date field. Room-based schedules can also
    carry a time slot and the rooms assigned to that exam.
    """

    date: DateType
    time_slot: TimeSlot | None = None
    rooms: tuple[Room, ...] = ()

    @property
    def total_capacity(self) -> int:
        """Return the total capacity of all rooms assigned to this placement."""
        return sum(room.capacity for room in self.rooms)
