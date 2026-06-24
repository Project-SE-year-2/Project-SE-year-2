from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.models.enums import TimeSlot


@dataclass(frozen=True, slots=True)
class ExamBlock:
    """
    Represents one scheduling option in room-scheduling mode.

    A block is not the final assignment yet.
    It only says: this exam may be placed on this date and time slot.
    """

    date: date
    time_slot: TimeSlot