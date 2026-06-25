from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.models.enums import TimeSlot


@dataclass(frozen=True, slots=True)
class ExamBlock:
    """
    Represents one scheduling option in room-scheduling mode.

    Example:
        date=date(2026, 7, 1)
        time_slot=TimeSlot.MORNING
    """

    date: date
    time_slot: TimeSlot
