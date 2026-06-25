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
        all_placements = list(schedule.iter_placements())

        # Bypass: if no placement has room data the constraint does not apply.
        if not any(p.is_room_based for _, _, p in all_placements):
            return True

        # (building, room_id, date, time_slot) — building is required because
        # the same room number can exist in different buildings (e.g. "101" in
        # building "1" and "101" in building "2" are distinct physical rooms).
        occupied: set[tuple] = set()

        for _, course, placement in all_placements:
            if not placement.is_room_based:
                continue

            # Rule 1 — room exclusivity per physical room
            for room in placement.rooms:
                key = (room.building, room.room_id, placement.date, placement.time_slot)
                if key in occupied:
                    return False
                occupied.add(key)

            # Rule 2 — capacity
            # A room-based placement with no valid student count is always
            # invalid: the normal solver path blocks this via
            # RoomSchedulingFeasibilityChecker, but manually constructed
            # schedules may bypass that check.
            num_students = getattr(course, "num_students", 0)
            if num_students <= 0:
                return False
            if placement.total_capacity < num_students:
                return False

        return True
