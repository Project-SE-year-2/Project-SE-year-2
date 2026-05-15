import pytest
from src.models.course import Course
from src.models.program_requirement import ProgramRequirement

def test_program_requirement_is_obligatory():
    req_ob = ProgramRequirement("83101", 1, "FALL", "Obligatory")
    req_el = ProgramRequirement("83102", 2, "SPRI", "Elective")

    assert req_ob.is_obligatory() is True
    assert req_el.is_obligatory() is False

def test_program_requirement_prevents_duplicate_courses():
    req = ProgramRequirement("83101", 1, "FALL", "Obligatory")
    
    req.add_course("Physics 1")
    req.add_course("Math 1")
    req.add_course("Physics 1") # This is a duplicate, should be ignored

    assert len(req.courses) == 2
    assert "Physics 1" in req.courses
    assert "Math 1" in req.courses

def test_course_belongs_to_program():
    course = Course("Physics 1", "83102", "Prof. O. Some", "Exam")
    
    # Add requirements for programs 83101 and 83102
    course.add_requirement(ProgramRequirement("83101", 1, "FALL", "Obligatory"))
    course.add_requirement(ProgramRequirement("83102", 1, "FALL", "Obligatory"))

    assert course.belongsToProgram("83101") is True
    assert course.belongsToProgram("83102") is True
    
    # Test for a program ID that does not exist in the course requirements
    assert course.belongsToProgram("99999") is False