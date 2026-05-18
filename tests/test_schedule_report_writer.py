import pytest
from datetime import date
from pathlib import Path

from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.models.program_requirement import ProgramRequirement
from src.output.schedule_report_writer import ScheduleReportWriter
from src.models.enums import Evaluation, Semester, Moed, ReqType


def test_report_contains_required_fields_in_exam_record(tmp_path):
    """
    Tests that every exam record written to the report contains:
    - Semester
    - Moed
    - Course name
    - Course ID
    - Instructor name
    - Exam date
    """
    writer = ScheduleReportWriter()

    period = ExamPeriod(
        Semester.FALL,
        Moed.Aleph,
        "01-02-2026",
        "02-02-2026"
    )

    course = Course(
        "Physics 1",
        "83102",
        "Prof. A",
        Evaluation.Exam
    )

    schedule = ExamSchedule(period)
    schedule.assign(course, date(2026, 2, 1))

    schedules = [schedule]

    metadata = {
        period: {
            "courses": [course],
            "available_days": 2,
            "theoretical_count": 2,
            "valid_count": 1,
        }
    }

    output_file = tmp_path / "schedule_output.txt"

    writer.write(
        schedules,
        metadata,
        ["83101"],
        output_path=str(output_file)
    )

    content = output_file.read_text(encoding="utf-8")

    assert "FALL" in content
    assert "Aleph" in content
    assert "Physics 1" in content
    assert "83102" in content
    assert "Prof. A" in content
    assert "01-02-2026" in content

def test_report_multi_level_sorting_by_semester_moed_date(tmp_path):
    """
    Tests that schedules in the generated report are ordered according to:
    FALL Aleph -> FALL Bet -> SPRI,
    and then by exam date inside each period.
    """
    writer = ScheduleReportWriter()

    fall_aleph = ExamPeriod(
        Semester.FALL,
        Moed.Aleph,
        "01-02-2026",
        "01-02-2026"
    )

    fall_bet = ExamPeriod(
        Semester.FALL,
        Moed.Bet,
        "10-04-2026",
        "10-04-2026"
    )

    spri_aleph = ExamPeriod(
        Semester.SPRI,
        Moed.Aleph,
        "01-07-2026",
        "01-07-2026"
    )

    c1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)
    c2 = Course("Calculus 1", "83112", "Prof. B", Evaluation.Exam)
    c3 = Course("Algorithms", "83222", "Prof. C", Evaluation.Exam)

    s1 = ExamSchedule(fall_bet)
    s1.assign(c1, date(2026, 4, 10))

    s2 = ExamSchedule(spri_aleph)
    s2.assign(c2, date(2026, 7, 1))

    s3 = ExamSchedule(fall_aleph)
    s3.assign(c3, date(2026, 2, 1))

    merged = s1.merge(s2)
    merged = merged.merge(s3)

    metadata = {
        fall_aleph: {
            "courses": [c3],
            "available_days": 1,
            "theoretical_count": 1,
            "valid_count": 1,
        },
        fall_bet: {
            "courses": [c1],
            "available_days": 1,
            "theoretical_count": 1,
            "valid_count": 1,
        },
        spri_aleph: {
            "courses": [c2],
            "available_days": 1,
            "theoretical_count": 1,
            "valid_count": 1,
        },
    }

    output_file = tmp_path / "schedule_output.txt"

    writer.write(
        [merged],
        metadata,
        ["83101"],
        output_path=str(output_file)
    )

    content = output_file.read_text(encoding="utf-8")

    fall_aleph_index = content.index("Algorithms")
    fall_bet_index = content.index("Physics 1")
    spri_aleph_index = content.index("Calculus 1")

    assert fall_aleph_index < fall_bet_index < spri_aleph_index


def test_report_total_complete_schedules_count(tmp_path):
    """
    Tests that the report displays the correct total number
    of complete schedules.
    """
    writer = ScheduleReportWriter()

    period = ExamPeriod(
        Semester.FALL,
        Moed.Aleph,
        "01-02-2026",
        "02-02-2026"
    )

    course = Course(
        "Physics 1",
        "83102",
        "Prof. A",
        Evaluation.Exam
    )

    schedule1 = ExamSchedule(period)
    schedule1.assign(course, date(2026, 2, 1))

    schedule2 = ExamSchedule(period)
    schedule2.assign(course, date(2026, 2, 2))

    metadata = {
        period: {
            "courses": [course],
            "available_days": 2,
            "theoretical_count": 2,
            "valid_count": 2,
        }
    }

    output_file = tmp_path / "schedule_output.txt"

    writer.write(
        [schedule1, schedule2],
        metadata,
        ["83101"],
        output_path=str(output_file)
    )

    content = output_file.read_text(encoding="utf-8")

    assert "TOTAL COMPLETE SCHEDULES : 2" in content

def test_report_no_duplicate_courses_in_single_schedule(tmp_path):
    """
    Tests that a course appears exactly once in the actual exam assignment
    section of a single schedule.
    """
    writer = ScheduleReportWriter()

    period = ExamPeriod(
        Semester.FALL,
        Moed.Aleph,
        "01-02-2026",
        "02-02-2026"
    )

    course = Course(
        "Physics 1",
        "83102",
        "Prof. A",
        Evaluation.Exam
    )

    schedule = ExamSchedule(period)
    schedule.assign(course, date(2026, 2, 1))

    metadata = {
        period: {
            "courses": [course],
            "available_days": 2,
            "theoretical_count": 2,
            "valid_count": 1,
        }
    }

    output_file = tmp_path / "schedule_output.txt"

    writer.write(
        [schedule],
        metadata,
        ["83101"],
        output_path=str(output_file)
    )

    content = output_file.read_text(encoding="utf-8")

    exam_record_lines = [
        line for line in content.split("\n")
        if "83102" in line
        and "Prof. A" in line
        and "01-02-2026" in line
    ]

    assert len(exam_record_lines) == 1

def test_report_handles_no_valid_schedules_gracefully(tmp_path):
    """
    Tests that the report writer handles an empty schedules list
    without crashing and still writes a valid summary report.
    """
    writer = ScheduleReportWriter()

    period = ExamPeriod(
        Semester.FALL,
        Moed.Aleph,
        "01-02-2026",
        "02-02-2026"
    )

    course = Course(
        "Physics 1",
        "83102",
        "Prof. A",
        Evaluation.Exam
    )

    metadata = {
        period: {
            "courses": [course],
            "available_days": 2,
            "theoretical_count": 2,
            "valid_count": 0,
        }
    }

    output_file = tmp_path / "schedule_output.txt"

    writer.write(
        [],
        metadata,
        ["83101"],
        output_path=str(output_file)
    )

    content = output_file.read_text(encoding="utf-8")

    assert "EXAM SCHEDULE GENERATOR - RESULTS" in content
    assert "TOTAL COMPLETE SCHEDULES : 0" in content
    assert "Valid          : 0" in content


def test_report_multiple_programs_displayed_correctly(tmp_path):
    """
    Tests that when multiple programs are selected,
    all selected program IDs appear correctly in the report header.
    """
    writer = ScheduleReportWriter()

    period = ExamPeriod(
        Semester.FALL,
        Moed.Aleph,
        "01-02-2026",
        "02-02-2026"
    )

    course = Course(
        "Physics 1",
        "83102",
        "Prof. A",
        Evaluation.Exam
    )

    schedule = ExamSchedule(period)
    schedule.assign(course, date(2026, 2, 1))

    metadata = {
        period: {
            "courses": [course],
            "available_days": 2,
            "theoretical_count": 2,
            "valid_count": 1,
        }
    }

    output_file = tmp_path / "schedule_output.txt"

    writer.write(
        [schedule],
        metadata,
        ["83101", "83102", "83108"],
        output_path=str(output_file)
    )

    content = output_file.read_text(encoding="utf-8")

    assert "Selected Programs : 83101, 83102, 83108" in content