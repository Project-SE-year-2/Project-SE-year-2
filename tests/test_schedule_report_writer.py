import pytest
from datetime import date
from pathlib import Path

from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.models.program_requirement import ProgramRequirement
from src.output.schedule_report_writer import ScheduleReportWriter


# Tests that each exam record line in the schedule section contains all required fields:
# Date, Course Name, Course ID, and Instructor Name.
def test_report_contains_required_fields_in_exam_record(tmp_path):
    """
    Verify that every exam record line explicitly includes all mandatory fields:
    Date, Course Name, Course ID, and Instructor Name.
    """
    course = Course("Physics 1", "83102", "Prof. A", "Exam")
    course.add_requirement(ProgramRequirement("83101", 1, "FALL", "Obligatory"))

    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "02-02-2026")
    period.possible_dates = [date(2026, 2, 1)]

    schedule = ExamSchedule(period)
    schedule.assign(course, date(2026, 2, 1))

    metadata = {
        period: {
            "courses": [course],
            "available_days": 1,
            "valid_count": 1,
            "theoretical_count": 1,
        }
    }

    output_file = tmp_path / "output.txt"
    writer = ScheduleReportWriter()
    writer.write([schedule], metadata, ["83101"], str(output_file))

    content = output_file.read_text(encoding="utf-8")

    # Verify all required fields are present in the schedule section
    assert "01-02-2026" in content  # Date
    assert "Physics 1" in content  # Course Name
    assert "83102" in content  # Course ID
    assert "Prof. A" in content  # Instructor Name

# Tests that the output schedules are sorted first by semester, then by moed,
# and then chronologically by date.
def test_report_multi_level_sorting_by_semester_moed_date(tmp_path):
    """
    Verify that the output text is strictly ordered by:
    1. Semester (Fall before Spring)
    2. Moed (Aleph before Bet)
    3. Chronologically by Date
    """
    # Create courses and periods
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(ProgramRequirement("83101", 1, "FALL", "Obligatory"))

    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")
    course2.add_requirement(ProgramRequirement("83101", 1, "SPRI", "Obligatory"))

    course3 = Course("Chemistry 1", "83103", "Prof. C", "Exam")
    course3.add_requirement(ProgramRequirement("83101", 1, "FALL", "Obligatory"))

    fall_aleph = ExamPeriod("FALL", "Aleph", "01-02-2026", "05-02-2026")
    fall_aleph.possible_dates = [
        date(2026, 2, 1),
        date(2026, 2, 2),
        date(2026, 2, 3),
    ]

    fall_bet = ExamPeriod("FALL", "Bet", "10-02-2026", "15-02-2026")
    fall_bet.possible_dates = [date(2026, 2, 10)]

    spri_aleph = ExamPeriod("SPRI", "Aleph", "01-07-2026", "05-07-2026")
    spri_aleph.possible_dates = [date(2026, 7, 1)]

    # Create multiple schedules to verify sorting
    schedule1 = ExamSchedule(fall_aleph)
    schedule1.assign(course1, date(2026, 2, 1))
    
    schedule_fall_bet = ExamSchedule(fall_bet)
    schedule_fall_bet.assign(course3, date(2026, 2, 10))
    schedule1_fall_bet = schedule1.merge(schedule_fall_bet)
    
    schedule_spri = ExamSchedule(spri_aleph)
    schedule_spri.assign(course2, date(2026, 7, 1))
    schedule1_full = schedule1_fall_bet.merge(schedule_spri)

    metadata = {
        fall_aleph: {
            "courses": [course1],
            "available_days": 3,
            "valid_count": 1,
            "theoretical_count": 3,
        },
        fall_bet: {
            "courses": [course3],
            "available_days": 1,
            "valid_count": 1,
            "theoretical_count": 1,
        },
        spri_aleph: {
            "courses": [course2],
            "available_days": 1,
            "valid_count": 1,
            "theoretical_count": 1,
        },
    }

    output_file = tmp_path / "output.txt"
    writer = ScheduleReportWriter()
    writer.write([schedule1_full], metadata, ["83101"], str(output_file))

    content = output_file.read_text(encoding="utf-8")

    # Verify FALL appears before SPRI
    fall_pos = content.find("FALL")
    spri_pos = content.find("SPRI")
    assert fall_pos < spri_pos, "FALL should appear before SPRI in output"

    # Verify Aleph appears before Bet within FALL
    aleph_pos = content.find("Aleph")
    bet_pos = content.find("Bet")
    assert aleph_pos < bet_pos, "Aleph should appear before Bet within FALL"

    # Verify dates are in chronological order within each period
    date1_pos = content.find("01-02-2026")
    date2_pos = content.find("10-02-2026")
    date3_pos = content.find("01-07-2026")
    assert date1_pos < date2_pos < date3_pos, "Dates should be in chronological order within periods"


# Tests that the total count of complete schedules is correctly displayed
# and matches the number of schedules passed.
def test_report_total_complete_schedules_count(tmp_path):
    """
    Verify that the total count of complete schedules is correctly displayed
    and matches the number of schedules passed.
    """
    course = Course("Physics 1", "83102", "Prof. A", "Exam")
    course.add_requirement(ProgramRequirement("83101", 1, "FALL", "Obligatory"))

    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "02-02-2026")
    period.possible_dates = [date(2026, 2, 1), date(2026, 2, 2)]

    schedule1 = ExamSchedule(period)
    schedule1.assign(course, date(2026, 2, 1))

    schedule2 = ExamSchedule(period)
    schedule2.assign(course, date(2026, 2, 2))

    metadata = {
        period: {
            "courses": [course],
            "available_days": 2,
            "valid_count": 2,
            "theoretical_count": 2,
        }
    }

    output_file = tmp_path / "output.txt"
    writer = ScheduleReportWriter()
    writer.write([schedule1, schedule2], metadata, ["83101"], str(output_file))

    content = output_file.read_text(encoding="utf-8")

    # Verify total count is present and matches
    assert "TOTAL COMPLETE SCHEDULES : 2" in content

# Tests that a specific course is never scheduled more than once within the same semester
# in a single schedule option.
def test_report_no_duplicate_courses_in_single_schedule(tmp_path):
    """
    Verify that a specific course is never scheduled more than once
    within the same semester in a single schedule option.
    """
    course = Course("Physics 1", "83102", "Prof. A", "Exam")
    course.add_requirement(ProgramRequirement("83101", 1, "FALL", "Obligatory"))

    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "02-02-2026")
    period.possible_dates = [date(2026, 2, 1), date(2026, 2, 2)]

    schedule = ExamSchedule(period)
    schedule.assign(course, date(2026, 2, 1))

    metadata = {
        period: {
            "courses": [course],
            "available_days": 2,
            "valid_count": 1,
            "theoretical_count": 2,
        }
    }

    output_file = tmp_path / "output.txt"
    writer = ScheduleReportWriter()
    writer.write([schedule], metadata, ["83101"], str(output_file))

    content = output_file.read_text(encoding="utf-8")

    # Count occurrences of the course in the actual schedule output
    # (not in the metadata section)
    lines = content.split("\n")
    schedule_section_started = False
    course_count = 0
    for line in lines:
        if "Complete Exam Schedules" in line:
            schedule_section_started = True
        if schedule_section_started and "83102" in line and "Courses" not in line:
            course_count += 1

    assert course_count == 1, "Course should appear exactly once per schedule"

# Tests that the report writer handles an empty schedules list gracefully
# by generating a proper report format indicating that zero valid options were found.
def test_report_handles_no_valid_schedules_gracefully(tmp_path):
    """
    Test the system with an empty schedules list, ensuring it outputs
    a message indicating no valid schedule was found.
    """
    course = Course("Physics 1", "83102", "Prof. A", "Exam")
    course.add_requirement(ProgramRequirement("83101", 1, "FALL", "Obligatory"))

    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "02-02-2026")
    period.possible_dates = [date(2026, 2, 1)]

    metadata = {
        period: {
            "courses": [course],
            "available_days": 1,
            "valid_count": 0,
            "theoretical_count": 1,
        }
    }

    output_file = tmp_path / "output.txt"
    writer = ScheduleReportWriter()

    # Should not crash even with empty schedules
    writer.write([], metadata, ["83101"], str(output_file))

    content = output_file.read_text(encoding="utf-8")

    # Verify file was created and contains metadata
    assert "EXAM SCHEDULE GENERATOR - RESULTS" in content
    assert "TOTAL COMPLETE SCHEDULES : 0" in content


# Tests that when multiple programs are selected, they all appear correctly
# in the output header.
def test_report_multiple_programs_displayed_correctly(tmp_path):
    """
    Verify that when multiple programs are selected, they all appear
    correctly in the output header.
    """
    course = Course("Physics 1", "83102", "Prof. A", "Exam")
    course.add_requirement(ProgramRequirement("83101", 1, "FALL", "Obligatory"))

    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "02-02-2026")
    period.possible_dates = [date(2026, 2, 1)]

    schedule = ExamSchedule(period)
    schedule.assign(course, date(2026, 2, 1))

    metadata = {
        period: {
            "courses": [course],
            "available_days": 1,
            "valid_count": 1,
            "theoretical_count": 1,
        }
    }

    output_file = tmp_path / "output.txt"
    writer = ScheduleReportWriter()
    writer.write(
        [schedule], metadata, ["83101", "83102", "83108"], str(output_file)
    )

    content = output_file.read_text(encoding="utf-8")

    # Verify all programs appear in the header
    assert "Selected Programs : 83101, 83102, 83108" in content