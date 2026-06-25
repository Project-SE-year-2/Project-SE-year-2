from datetime import date

from src.models.course import Course
from src.models.enums import Evaluation, Moed, Semester, TimeSlot
from src.models.exam_period import ExamPeriod
from src.models.exam_placement import ExamPlacement
from src.models.exam_schedule import ExamSchedule
from src.models.room import Room
from src.output.schedule_report_writer import ScheduleReportWriter


def _period() -> ExamPeriod:
    """Create a simple FALL Aleph exam period for export tests."""
    return ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 31))


def _course(students: int = 25) -> Course:
    """Create a course with a configurable number of students."""
    return Course("Algorithms", "89123", "Dr. Cohen", Evaluation.Exam, students)


def _write_report(tmp_path, schedule: ExamSchedule) -> str:
    """Write a schedule report and return its text content."""
    output_path = tmp_path / "report.txt"

    ScheduleReportWriter().write(
        schedules=[schedule],
        metadata={},
        programs=["83101"],
        output_path=str(output_path),
    )

    return output_path.read_text(encoding="utf-8")


def test_date_only_export_remains_unchanged(tmp_path):
    """Verify that date-only schedules do not include room-specific export columns."""
    period = _period()
    course = _course()
    schedule = ExamSchedule(period)

    schedule.assign(course, date(2026, 1, 10))

    text = _write_report(tmp_path, schedule)

    assert "Algorithms (89123)" in text
    assert "Dr. Cohen" in text
    assert "10-01-2026" in text
    assert "Time Slot" not in text
    assert "Assigned Rooms" not in text
    assert "Students" not in text
    assert "Capacity" not in text


def test_room_export_contains_required_columns(tmp_path):
    """Verify that room-based schedules include all room scheduling export columns."""
    period = _period()
    course = _course(students=40)
    room = Room(room_id="101", building="1", capacity=50)
    schedule = ExamSchedule(period)

    schedule.assign(
        course,
        ExamPlacement.with_rooms(
            date(2026, 1, 10),
            TimeSlot.MORNING,
            (room,),
        ),
    )

    text = _write_report(tmp_path, schedule)

    assert "Time Slot" in text
    assert "Assigned Rooms" in text
    assert "Students" in text
    assert "Capacity" in text
    assert "MORNING" in text
    assert "1-101" in text
    assert "40" in text
    assert "50" in text


def test_room_export_formats_multiple_rooms_as_comma_separated_string(tmp_path):
    """Verify that multiple assigned rooms are exported as a comma-separated string."""
    period = _period()
    course = _course(students=80)
    room1 = Room(room_id="101", building="1", capacity=50)
    room2 = Room(room_id="102", building="1", capacity=40)
    schedule = ExamSchedule(period)

    schedule.assign(
        course,
        ExamPlacement.with_rooms(
            date(2026, 1, 10),
            TimeSlot.AFTERNOON,
            (room1, room2),
        ),
    )

    text = _write_report(tmp_path, schedule)

    assert "AFTERNOON" in text
    assert "1-101, 1-102" in text
    assert "80" in text
    assert "90" in text

def test_export_does_not_duplicate_schedule_trailing_divider(tmp_path):
    """Verify that each schedule block has only one trailing divider."""
    period = _period()
    course = _course()
    schedule = ExamSchedule(period)
    schedule.assign(course, date(2026, 1, 10))

    text = _write_report(tmp_path, schedule)

    assert "\n  " + ("-" * 70) + "\n  " + ("-" * 70) not in text
