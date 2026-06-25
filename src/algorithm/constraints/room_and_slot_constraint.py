from __future__ import annotations

from src.algorithm.constraints.i_constraint import IConstraint
from src.models.exam_schedule import ExamSchedule


class RoomAndSlotConstraint(IConstraint):
    """
    Hard constraint that enforces two physical room rules across a schedule:

      1. Room exclusivity — a single room cannot host two different exams at
         the same (date, time_slot).  Each (room_id, date, slot) triple must
         appear at most once across all placements.

      2. Capacity — the combined capacity of the rooms assigned to an exam
         must be >= the number of registered students for that course.

    When room scheduling is disabled all placements carry no room data
    (is_room_based == False) and this constraint returns True immediately,
    so date-only mode is completely unaffected.
    """

    def is_satisfied(self, schedule: ExamSchedule) -> bool:
        placements = schedule.placements

        # Bypass: if no placement has room data the constraint does not apply.
        if not any(p.is_room_based for p in placements.values()):
            return True

        occupied: set[tuple] = set()  # (room_id, date, time_slot)

        for course, placement in placements.items():
            if not placement.is_room_based:
                # Mixed schedules are not expected, but skip gracefully.
                continue

            # Rule 1 — room exclusivity
            for room in placement.rooms:
                key = (room.room_id, placement.date, placement.time_slot)
                if key in occupied:
                    return False
                occupied.add(key)

            # Rule 2 — capacity
            num_students = getattr(course, "num_students", 0)
            if num_students > 0 and placement.total_capacity < num_students:
                return False

        return True
