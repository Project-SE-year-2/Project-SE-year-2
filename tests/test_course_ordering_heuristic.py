import pytest
from src.models.course import Course
from src.models.program_requirement import ProgramRequirement
from src.models.exam_period import ExamPeriod
from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.course_ordering_heuristic import CourseOrderingHeuristic

def test_order_by_most_constrained():
    """
    Tests that orderByMostConstrained properly sorts courses in descending order 
    based on the number of potential conflicts they share. Courses involved 
    in larger obligatory groups must appear first to enable early pruning.
    """
    # Setup courses with different constraint levels:
    # c3 belongs to an obligatory group with 2 other courses (total 2 potential conflicts)
    # c1 and c2 belong to a smaller group together (total 1 potential conflict each)
    c1 = Course("C1", "1", "A", "Exam")
    c1.add_requirement(ProgramRequirement("PROG1", 1, "FALL", "Obligatory"))
    
    c2 = Course("C2", "2", "B", "Exam")
    c2.add_requirement(ProgramRequirement("PROG1", 1, "FALL", "Obligatory"))

    c3 = Course("C3", "3", "C", "Exam")
    c3.add_requirement(ProgramRequirement("PROG2", 1, "FALL", "Obligatory"))
    
    c4 = Course("C4", "4", "D", "Exam")
    c4.add_requirement(ProgramRequirement("PROG2", 1, "FALL", "Obligatory"))
    
    c5 = Course("C5", "5", "E", "Exam")
    c5.add_requirement(ProgramRequirement("PROG2", 1, "FALL", "Obligatory"))

    index = ConstraintIndex()
    index.build([c1, c2, c3, c4, c5], ["PROG1", "PROG2"])

    heuristic = CourseOrderingHeuristic(index)
    period = ExamPeriod("FALL", "Aleph", "01-01-2026", "02-01-2026")
    
    ordered = heuristic.orderByMostConstrained([c1, c2, c3], period)
    
    # c3 has the most constraints, so it must be selected first
    assert ordered[0] == c3
    assert c1 in ordered[1:]
    assert c2 in ordered[1:]