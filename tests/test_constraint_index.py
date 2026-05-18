import pytest
from src.models.course import Course
from src.models.program_requirement import ProgramRequirement
from src.algorithm.constraint_index import ConstraintIndex

def test_constraint_index_builds_obligatory_groups():
    """
    Tests that ConstraintIndex correctly builds conflict groups based on 
    the (program_id, year, semester) key, ensuring that only 'Obligatory' 
    courses are grouped together while 'Elective' courses are ignored.
    """
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(ProgramRequirement("83101", 1, "FALL", "Obligatory"))

    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")
    course2.add_requirement(ProgramRequirement("83101", 1, "FALL", "Obligatory"))

    course3 = Course("Elective 1", "83113", "Prof. C", "Exam")
    course3.add_requirement(ProgramRequirement("83101", 1, "FALL", "Elective"))

    index = ConstraintIndex()
    index.build([course1, course2, course3], ["83101"])

    groups = index.obligatoryGroups()
    key = ("83101", 1, "FALL")
    
    assert key in groups
    assert course1 in groups[key]
    assert course2 in groups[key]
    assert course3 not in groups[key] # Electives should not be part of the obligatory group

def test_constraint_index_group_key_for():
    """
    Tests that groupKeyFor correctly extracts and formats the structural tuple key 
    for a given valid course matching the selected programs.
    """
    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course1.add_requirement(ProgramRequirement("83101", 1, "FALL", "Obligatory"))
    
    index = ConstraintIndex()
    index.build([course1], ["83101"])
    
    assert index.groupKeyFor(course1) == ("83101", 1, "FALL")