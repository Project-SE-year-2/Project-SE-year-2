from __future__ import annotations

from dataclasses import dataclass

from src.models.enums import TimeSlot


@dataclass(frozen=True, slots=True)
class ExamBlock:
    """
    A pure domain value representing one scheduling option: a specific date
    combined with a specific time slot.

    ExamBlock is produced by RoomSchedulingDomainProvider and consumed by
    RoomPlacementFactory, which converts it into an ExamPlacement by allocating
    the required rooms.  Keeping the two steps separate ensures that:

      - The domain provider only answers "which (date, slot) options exist?"
      - The placement factory answers "which rooms do we assign for this option?"
    """

    date: date
    time_slot: TimeSlot
