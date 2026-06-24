from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.models.enums import TimeSlot


@dataclass(frozen=True, slots=True)
class ExamBlock:
    """
    Represents one scheduling option in room-scheduling mode.

    Example:
        date=01/07/2026
        time_slot=TimeSlot.MORNING
    """

    date: date
    time_slot: TimeSlot