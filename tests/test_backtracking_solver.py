import pytest
from datetime import date
from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.program_requirement import ProgramRequirement
from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.basic_version_validator import BasicVersionValidator
from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.course_ordering_heuristic import CourseOrderingHeuristic
from src.algorithm.forward_checker import ForwardChecker
from src.algorithm.backtracking_solver import BacktrackingSolver

def _setup_solver(courses, programs):
    index = ConstraintIndex()
    index.build(courses, programs)
    collision_validator = BasicVersionValidator(index)
    validator = ConstraintValidator(index, collision_validator)
    heuristic = CourseOrderingHeuristic(index)
    checker = ForwardChecker(validator)
    
    solver = BacktrackingSolver(collision_validator, heuristic, checker)
    return solver, validator

def test_solver_finds_all_solutions_no_conflicts():
    """
    Tests that BacktrackingSolver successfully finds all theoretically possible 
    valid schedules when courses do not have any shared obligatory constraints.
    """
    c1 = Course("C1", "1", "A", "Exam")
    c2 = Course("C2", "2", "B", "Exam")
    
    solver, validator = _setup_solver([c1, c2], ["83101"])
    period = ExamPeriod("FALL", "Aleph", "01-01-2026", "02-01-2026")
    period.possible_dates = [date(2026, 1, 1), date(2026, 1, 2)]
    
    # 2 independent courses assigned over 2 available days = 2 * 2 = 4 total possibilities
    schedules = solver.solve([c1, c2], period, validator)
    assert len(schedules) == 4

def test_solver_returns_empty_when_impossible():
    """
    Tests that BacktrackingSolver correctly returns an empty list when 
    obligatory constraints cannot be satisfied given the limited number 
    of available exam dates.
    """
    c1 = Course("C1", "1", "A", "Exam")
    c1.add_requirement(ProgramRequirement("83101", 1, "FALL", "Obligatory"))
    c2 = Course("C2", "2", "B", "Exam")
    c2.add_requirement(ProgramRequirement("83101", 1, "FALL", "Obligatory"))
    
    solver, validator = _setup_solver([c1, c2], ["83101"])
    period = ExamPeriod("FALL", "Aleph", "01-01-2026", "01-01-2026")
    period.possible_dates = [date(2026, 1, 1)] 
    
    # Two obligatory courses from the same year/semester cannot share the single available day
    schedules = solver.solve([c1, c2], period, validator)
    assert len(schedules) == 0

def test_solver_with_empty_courses():
    """
    Tests that passing an empty list of courses to the solver returns 
    exactly one valid empty schedule without crashing.
    """
    solver, validator = _setup_solver([], ["83101"])
    period = ExamPeriod("FALL", "Aleph", "01-01-2026", "02-01-2026")
    schedules = solver.solve([], period, validator)
    
    assert len(schedules) == 1
    assert len(schedules[0].assignments) == 0