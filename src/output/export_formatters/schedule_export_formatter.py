from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_placement import ExamPlacement
from src.models.exam_schedule import ExamSchedule
from src.models.enums import TimeSlot


_TIME_SLOT_ORDER = {
    TimeSlot.MORNING: 0,
    TimeSlot.AFTERNOON: 1,
    TimeSlot.EVENING: 2,
}


class ScheduleExportFormatter(ABC):
    """Formats one ExamSchedule into report lines."""

    @abstractmethod
    def format_schedule(self, schedule: ExamSchedule, index: int, divider: str) -> list[str]:
        """Return formatted report lines for one schedule."""
        raise NotImplementedError


class DateOnlyExportFormatter(ScheduleExportFormatter):
    """Formats schedules using the existing date-only export layout."""

    def format_schedule(self, schedule: ExamSchedule, index: int, divider: str) -> list[str]:
        """Return the legacy export format without room-specific columns."""
        lines = [
            f"  Schedule #{index}",
            f"  {divider}",
        ]

        current_sem = None
        current_moed = None

        for period, course, placement in _sorted_placements(schedule):
            sem = _enum_value(period.semester)
            moed = _enum_value(period.moed)

            if sem != current_sem:
                current_sem = sem
                current_moed = None
                lines.append(f"  {sem}")

            if moed != current_moed:
                current_moed = moed
                lines.append(f"    {moed}")

            course_field = f"{course.name} ({course.course_id})"
            lines.append(
                f"      {course_field:<35} "
                f"{course.instructor:<25} "
                f"{placement.date.strftime('%d-%m-%Y')}"
            )

        lines.append(f"  {divider}")
        lines.append("")
        return lines


class RoomExportFormatter(ScheduleExportFormatter):
    """Formats room-based schedules with room scheduling export columns."""

    def format_schedule(self, schedule: ExamSchedule, index: int, divider: str) -> list[str]:
        """Return room-aware export lines including time slot, rooms, students, and capacity."""
        lines = [
            f"  Schedule #{index}",
            f"  {divider}",
        ]

        current_sem = None
        current_moed = None

        for period, course, placement in _sorted_placements(schedule):
            sem = _enum_value(period.semester)
            moed = _enum_value(period.moed)

            if sem != current_sem:
                current_sem = sem
                current_moed = None
                lines.append(f"  {sem}")

            if moed != current_moed:
                current_moed = moed
                lines.append(f"    {moed}")
                lines.append(
                    "      "
                    f"{'Course':<35} "
                    f"{'Instructor':<25} "
                    f"{'Date':<12} "
                    f"{'Time Slot':<12} "
                    f"{'Assigned Rooms':<25} "
                    f"{'Students':<10} "
                    f"{'Capacity':<10}"
                )

            course_field = f"{course.name} ({course.course_id})"
            lines.append(
                "      "
                f"{course_field:<35} "
                f"{course.instructor:<25} "
                f"{placement.date.strftime('%d-%m-%Y'):<12} "
                f"{_format_time_slot(placement):<12} "
                f"{_format_rooms(placement):<25} "
                f"{getattr(course, 'num_students', 0):<10} "
                f"{placement.total_capacity:<10}"
            )

        lines.append(f"  {divider}")
        lines.append("")
        return lines


class ExportFormatterFactory:
    """Selects the correct export formatter based on schedule contents."""

    @staticmethod
    def create(schedule: ExamSchedule) -> ScheduleExportFormatter:
        """Return RoomExportFormatter when schedule contains room data, otherwise DateOnlyExportFormatter."""
        if any(placement.is_room_based for _, _, placement in schedule.iter_placements()):
            return RoomExportFormatter()

        return DateOnlyExportFormatter()


def _sorted_placements(schedule: ExamSchedule) -> list[tuple[ExamPeriod, Course, ExamPlacement]]:
    """Return placements sorted by period, date, and time slot."""
    return sorted(
        schedule.iter_placements(),
        key=lambda item: (
            _enum_value(item[0].semester),
            _enum_value(item[0].moed),
            item[2].date,
            _time_slot_sort_value(item[2]),
            item[1].course_id,
        ),
    )


def _time_slot_sort_value(placement: ExamPlacement) -> int:
    """Return the sorting value for a placement time slot."""
    if placement.time_slot is None:
        return -1

    return _TIME_SLOT_ORDER.get(placement.time_slot, 99)


def _format_rooms(placement: ExamPlacement) -> str:
    """Return assigned rooms as a comma-separated string."""
    if not placement.rooms:
        return ""

    return ", ".join(
        f"{room.building}-{room.room_id}"
        for room in placement.rooms
    )


def _format_time_slot(placement: ExamPlacement) -> str:
    """Return the time slot string for export."""
    if placement.time_slot is None:
        return ""

    return placement.time_slot.value


def _enum_value(value) -> str:
    """Return enum.value when available, otherwise str(value)."""
    return value.value if hasattr(value, "value") else str(value)
