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

# Tests that a single course with N available days creates exactly N schedules.
def test_solver_single_course_with_multiple_days():
    c1 = Course("C1", "1", "A", "Exam")

    solver, validator = _setup_solver([c1], ["83101"])

    period = ExamPeriod("FALL", "Aleph", "01-01-2026", "03-01-2026")
    period.possible_dates = [
        date(2026, 1, 1),
        date(2026, 1, 2),
        date(2026, 1, 3),
    ]

    schedules = solver.solve([c1], period, validator)

    assert len(schedules) == 3

    assigned_dates = {s.assignments[c1] for s in schedules}

    assert assigned_dates == set(period.possible_dates)


# Tests that conflicts apply only to courses in the same obligatory group,
# while non-conflicting courses may still share dates.
def test_solver_three_courses_some_conflict_some_not():
    c1 = Course("C1", "1", "A", "Exam")
    c1.add_requirement(ProgramRequirement("83101", 1, "FALL", "Obligatory"))

    c2 = Course("C2", "2", "B", "Exam")
    c2.add_requirement(ProgramRequirement("83101", 1, "FALL", "Obligatory"))

    c3 = Course("C3", "3", "C", "Exam")
    c3.add_requirement(ProgramRequirement("83108", 1, "FALL", "Obligatory"))

    solver, validator = _setup_solver([c1, c2, c3], ["83101", "83108"])

    period = ExamPeriod("FALL", "Aleph", "01-01-2026", "02-01-2026")
    period.possible_dates = [
        date(2026, 1, 1),
        date(2026, 1, 2),
    ]

    schedules = solver.solve([c1, c2, c3], period, validator)

    assert len(schedules) > 0

    for schedule in schedules:
        assignments = schedule.assignments

        assert assignments[c1] != assignments[c2]
        assert assignments[c3] in period.possible_dates


# Tests that the solver can handle a moderately larger input
# without crashing and still returns valid schedules.
def test_solver_sanity_load_many_courses_many_days():
    courses = []

    for i in range(5):
        course = Course(f"C{i}", str(i), "A", "Exam")
        course.add_requirement(
            ProgramRequirement("83101", 1, "FALL", "Obligatory")
        )
        courses.append(course)

    solver, validator = _setup_solver(courses, ["83101"])

    period = ExamPeriod("FALL", "Aleph", "01-01-2026", "07-01-2026")
    period.possible_dates = [
        date(2026, 1, day)
        for day in range(1, 8)
    ]

    schedules = solver.solve(courses, period, validator)

    assert len(schedules) > 0

    for schedule in schedules:
        assignments = schedule.assignments

        assert len(assignments) == 5
        assert len(set(assignments.values())) == 5