import pytest
from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.program_requirement import ProgramRequirement
# Adjust the import path based on where match_courses_to_periods is actually located
from src.algorithm.scheduling_algoritem import match_courses_to_periods

def test_match_single_period_multiple_programs():
    # Setup a single exam period
    fall_period = ExamPeriod("FALL", "Aleph", "01-01-2026", "31-01-2026")
    periods = [fall_period]

    # Setup a course required by multiple programs in the same semester
    c1 = Course("Calculus 1", "83112", "Dr. Erez", "Exam")
    c1.add_requirement(ProgramRequirement("SE", 1, "FALL", "Obligatory"))
    c1.add_requirement(ProgramRequirement("CS", 1, "FALL", "Obligatory"))
    # Add a requirement for a different program in a different semester to ensure it's ignored
    c1.add_requirement(ProgramRequirement("EE", 1, "SPRI", "Obligatory"))

    valid_courses = [c1]

    # Execute the function
    result = match_courses_to_periods(valid_courses, periods)

    # Assertions
    assert fall_period in result
    assert c1 in result[fall_period]
    
    programs = result[fall_period][c1]
    assert len(programs) == 2
    assert "SE" in programs
    assert "CS" in programs
    assert "EE" not in programs

def test_course_split_across_different_semesters():
    # Setup two distinct exam periods
    fall_period = ExamPeriod("FALL", "Aleph", "01-01-2026", "31-01-2026")
    spri_period = ExamPeriod("SPRI", "Aleph", "01-06-2026", "30-06-2026")
    periods = [fall_period, spri_period]

    # Setup a course that is taken in FALL by SE, but in SPRI by Data
    c2 = Course("Physics 1", "83101", "Prof. Some", "Exam")
    c2.add_requirement(ProgramRequirement("SE", 1, "FALL", "Obligatory"))
    c2.add_requirement(ProgramRequirement("Data", 1, "SPRI", "Obligatory"))

    valid_courses = [c2]

    # Execute the function
    result = match_courses_to_periods(valid_courses, periods)

    # Assert FALL period constraints
    assert c2 in result[fall_period]
    assert result[fall_period][c2] == ["SE"]

    # Assert SPRI period constraints
    assert c2 in result[spri_period]
    assert result[spri_period][c2] == ["Data"]

def test_whitespace_and_case_handling():
    # Setup period and course with messy whitespace strings
    # The strip() function inside the logic should handle this smoothly
    messy_period = ExamPeriod(" FALL ", "Aleph", "01-01-2026", "31-01-2026")
    c3 = Course("Data Structures", "102", "Dr. Jane", "Exam")
    c3.add_requirement(ProgramRequirement("SE", 1, "FALL\n", "Obligatory"))
    
    result = match_courses_to_periods([c3], [messy_period])
    
    # Assertions
    assert messy_period in result
    assert c3 in result[messy_period]
    assert "SE" in result[messy_period][c3]

def test_empty_lists():
    fall_period = ExamPeriod("FALL", "Aleph", "01-01-2026", "31-01-2026")
    c4 = Course("Math", "101", "T", "Exam")
    
    # Test 1: Empty courses list
    result_empty_courses = match_courses_to_periods([], [fall_period])
    assert fall_period in result_empty_courses
    assert len(result_empty_courses[fall_period]) == 0

    # Test 2: Empty periods list
    result_empty_periods = match_courses_to_periods([c4], [])
    assert result_empty_periods == {}