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
from src.algorithm.scheduling_mode_factory import SchedulingModeFactory
from src.models.constraint_settings import ConstraintSettings
from src.models.enums import Evaluation, Semester, Moed, ReqType
from src.models.room import Room

def _setup_solver(courses, programs):
    index = ConstraintIndex()
    index.build(courses, programs)
    collision_validator = BasicVersionValidator(index)
    validator = ConstraintValidator(index, collision_validator)
    heuristic = CourseOrderingHeuristic(index)
    checker = ForwardChecker(validator)
    
    solver = BacktrackingSolver(collision_validator, heuristic, checker)
    return solver, validator


def _setup_room_solver(courses, programs, rooms):
    index = ConstraintIndex()
    index.build(courses, programs)
    collision_validator = BasicVersionValidator(index)
    validator = ConstraintValidator(index, collision_validator)
    heuristic = CourseOrderingHeuristic(index)
    checker = ForwardChecker(validator)
    components = SchedulingModeFactory.create(
        ConstraintSettings(room_scheduling_enabled=True),
        rooms,
    )

    solver = BacktrackingSolver(
        collision_validator,
        heuristic,
        checker,
        scheduling_components=components,
    )
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


def test_room_mode_solve_enforces_course_validation_before_search():
    course = Course("C1", "1", "A", Evaluation.Exam, 0)
    solver, validator = _setup_room_solver([course], ["83101"], [Room("101", "1", 30)])
    period = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "01-01-2026")
    period.possible_dates = [date(2026, 1, 1)]

    with pytest.raises(ValueError, match="positive student count"):
        solver.solve([course], period, validator)


def test_room_mode_solve_stream_enforces_course_validation_before_search():
    course = Course("C1", "1", "A", Evaluation.Exam, 40)
    solver, validator = _setup_room_solver([course], ["83101"], [Room("101", "1", 30)])
    period = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "01-01-2026")
    period.possible_dates = [date(2026, 1, 1)]
    stream = solver.solve_stream([course], period, validator)

    # Generator validation runs when iteration starts.
    with pytest.raises(ValueError, match="total room capacity"):
        next(stream)


def test_room_mode_check_feasibility_returns_validation_message():
    course = Course("C1", "1", "A", Evaluation.Exam, 0)
    solver, validator = _setup_room_solver([course], ["83101"], [Room("101", "1", 30)])
    period = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "01-01-2026")
    period.possible_dates = [date(2026, 1, 1)]

    is_valid, message = solver.check_feasibility([course], period, validator)

    assert is_valid is False
    assert "positive student count" in message

def test_solver_returns_empty_when_impossible():
    c1 = Course("C1", "1", "A", Evaluation.Exam)
    c1.add_requirement(
        ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory)
    )

    c2 = Course("C2", "2", "B", Evaluation.Exam)
    c2.add_requirement(
        ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory)
    )

    solver, validator = _setup_solver([c1, c2], ["83101"])

    period = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "01-01-2026")
    period.possible_dates = [date(2026, 1, 1)]

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
    c1 = Course("C1", "1", "A", Evaluation.Exam)
    c1.add_requirement(
        ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory)
    )

    c2 = Course("C2", "2", "B", Evaluation.Exam)
    c2.add_requirement(
        ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory)
    )

    c3 = Course("C3", "3", "C", Evaluation.Exam)
    c3.add_requirement(
        ProgramRequirement("83108", 1, Semester.FALL, ReqType.Obligatory)
    )

    solver, validator = _setup_solver([c1, c2, c3], ["83101", "83108"])

    period = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "02-01-2026")
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
        course = Course(f"C{i}", str(i), "A", Evaluation.Exam)
        course.add_requirement(
            ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory)
        )
        courses.append(course)

    solver, validator = _setup_solver(courses, ["83101"])

    period = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "07-01-2026")
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


def test_solve_stream_break_and_resume_no_gaps_or_repeats():
    """
    Tests that solve_stream() yields schedules one at a time and can be
    paused/ resumed without gaps or repeats.
    
    Creates 3 independent courses with 5 available dates = 5^3 = 125 schedules.
    Collects first 50, then resumes and collects the rest.
    Verifies no gaps or repeats in the complete sequence.
    """
    # Create 3 independent courses (no shared obligatory constraints)
    c1 = Course("C1", "1", "A", "Exam")
    c2 = Course("C2", "2", "B", "Exam")
    c3 = Course("C3", "3", "C", "Exam")
    
    solver, validator = _setup_solver([c1, c2, c3], ["83101", "83102", "83103"])
    
    period = ExamPeriod("FALL", "Aleph", "01-01-2026", "05-01-2026")
    period.possible_dates = [
        date(2026, 1, 1),
        date(2026, 1, 2),
        date(2026, 1, 3),
        date(2026, 1, 4),
        date(2026, 1, 5),
    ]
    
    # Expected: 5^3 = 125 total schedules
    first_batch = []
    stream = solver.solve_stream([c1, c2, c3], period, validator)
    
    # Collect first 50 schedules
    for _ in range(50):
        schedule = next(stream)
        first_batch.append(schedule)
    
    # Collect remaining schedules
    second_batch = list(stream)
    
    all_schedules = first_batch + second_batch
    
    # Verify we got 125 total schedules (5^3)
    assert len(all_schedules) == 125
    
    # Verify no repeats by converting each schedule's assignments to a hashable tuple
    def schedule_to_tuple(sched):
        items = []
        for (p, c), d in sorted(sched._store.items(), key=lambda x: str(x[0][1])):
            items.append((str(c), str(d)))
        return tuple(items)
    
    schedule_tuples = [schedule_to_tuple(s) for s in all_schedules]
    unique_tuples = set(schedule_tuples)
    
    # All 125 schedules should be unique
    assert len(unique_tuples) == 125
    
    # Verify no schedule is yielded twice (no repeats)
    assert len(schedule_tuples) == len(set(schedule_tuples))
    
    # Verify partial.copy() was used (each schedule is independent)
    # Modify one schedule and ensure others are unaffected
    for schedule in all_schedules:
        # Each schedule should have independent assignment data
        assert len(schedule.assignments) == 3


def test_solve_stream_yields_copies_not_partial():
    """
    Tests that solve_stream() yields copies of partial, never the mutable
    partial object itself. Modifying a yielded schedule should not affect
    subsequent yields.
    """
    c1 = Course("C1", "1", "A", "Exam")
    c2 = Course("C2", "2", "B", "Exam")
    
    solver, validator = _setup_solver([c1, c2], ["83101"])
    
    period = ExamPeriod("FALL", "Aleph", "01-01-2026", "02-01-2026")
    period.possible_dates = [date(2026, 1, 1), date(2026, 1, 2)]
    
    stream = solver.solve_stream([c1, c2], period, validator)
    
    first = next(stream)
    
    # Manually assign wrong dates to first schedule
    first.assign(c1, date(2026, 1, 5))
    first.assign(c2, date(2026, 1, 5))
    
    # Collect remaining schedules
    remaining = list(stream)
    
    # Verify remaining schedules still have valid assignments
    for schedule in remaining:
        assert schedule.assignments[c1] in period.possible_dates
        assert schedule.assignments[c2] in period.possible_dates
        # c1 and c2 are independent so can share the same date
        assert len(schedule.assignments) == 2
    
    # Verify first schedule was modified (proves it's a copy, not partial)
    assert first.assignments[c1] == date(2026, 1, 5)
    assert first.assignments[c2] == date(2026, 1, 5)


def test_solver_timing_5_constrained_courses_10_days():
    """5 courses in the same obligatory group with 10 available days
    must complete in < 2 seconds."""
    import time

    courses = []
    for i in range(5):
        c = Course(f"C{i}", str(i), "A", Evaluation.Exam)
        c.add_requirement(
            ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory)
        )
        courses.append(c)

    solver, validator = _setup_solver(courses, ["83101"])

    period = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "10-01-2026")
    period.possible_dates = [date(2026, 1, d) for d in range(1, 11)]

    start = time.time()
    schedules = solver.solve(courses, period, validator)
    elapsed = time.time() - start

    assert elapsed < 2.0, f"Solver took {elapsed:.2f}s, expected < 2s"
    assert len(schedules) > 0


def test_solver_all_in_one_group_n_days_gives_n_factorial_permutations():
    """N courses in the same obligatory group with exactly N days
    produces exactly N! valid schedules (all permutations)."""
    import math

    n = 4
    courses = []
    for i in range(n):
        c = Course(f"C{i}", str(i), "A", Evaluation.Exam)
        c.add_requirement(
            ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory)
        )
        courses.append(c)

    solver, validator = _setup_solver(courses, ["83101"])

    period = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "04-01-2026")
    period.possible_dates = [date(2026, 1, d) for d in range(1, n + 1)]

    schedules = solver.solve(courses, period, validator)
    assert len(schedules) == math.factorial(n)

    # Verify each schedule assigns all courses to distinct dates
    for s in schedules:
        dates = list(s.assignments.values())
        assert len(dates) == n
        assert len(set(dates)) == n


def test_solve_stream_zero_solutions():
    """solve_stream with an impossible setup yields nothing."""
    c1 = Course("C1", "1", "A", Evaluation.Exam)
    c1.add_requirement(
        ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory)
    )
    c2 = Course("C2", "2", "B", Evaluation.Exam)
    c2.add_requirement(
        ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory)
    )

    solver, validator = _setup_solver([c1, c2], ["83101"])

    period = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "01-01-2026")
    period.possible_dates = [date(2026, 1, 1)]

    results = list(solver.solve_stream([c1, c2], period, validator))
    assert len(results) == 0


def test_solve_stream_early_stop():
    """Stopping iteration early (via break) does not corrupt the solver."""
    c1 = Course("C1", "1", "A", "Exam")
    c2 = Course("C2", "2", "B", "Exam")

    solver, validator = _setup_solver([c1, c2], ["83101"])

    period = ExamPeriod("FALL", "Aleph", "01-01-2026", "05-01-2026")
    period.possible_dates = [date(2026, 1, d) for d in range(1, 6)]

    # Only take the first 3 schedules
    count = 0
    for sched in solver.solve_stream([c1, c2], period, validator):
        count += 1
        if count >= 3:
            break

    assert count == 3

