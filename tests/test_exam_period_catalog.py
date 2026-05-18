import pytest
from src.models.exam_period import ExamPeriod
from src.models.course import Course
from src.models.program_requirement import ProgramRequirement
from src.algorithm.exam_period_catalog import ExamPeriodCatalog

def test_catalog_get_returns_correct_period():
    """
    Tests that the catalog correctly retrieves an ExamPeriod object using 
    the matching semester and moed identifiers, and returns None for non-existent ones.
    """
    p1 = ExamPeriod("FALL", "Aleph", "01-01-2026", "10-01-2026")
    p2 = ExamPeriod("SPRI", "Bet", "01-05-2026", "10-05-2026")
    catalog = ExamPeriodCatalog([p1, p2])

    assert catalog.get("FALL", "Aleph") == p1
    assert catalog.get("SPRI", "Bet") == p2
    assert catalog.get("FALL", "Bet") is None

def test_catalog_period_for_course():
    """
    Tests that periodFor correctly maps a Course object to its corresponding 
    ExamPeriod by matching the semester defined within the course's requirements.
    """
    p1 = ExamPeriod("FALL", "Aleph", "01-01-2026", "10-01-2026")
    catalog = ExamPeriodCatalog([p1])
    
    course = Course("Math", "101", "Dr. A", "Exam")
    course.add_requirement(ProgramRequirement("83101", 1, "FALL", "Obligatory"))

    assert catalog.periodFor(course, "Aleph") == p1