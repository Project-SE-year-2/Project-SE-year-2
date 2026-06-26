"""
Tests for EP-153: Time-Slot Conflict Rules.

Business rule: conflict detection (collision and gap) operates at the date level
only.  time_slot is intentionally ignored so that two exams scheduled on the same
calendar date are always a conflict, regardless of their assigned time slot.

Three test groups:

  Group A - unit, time slot does not prevent conflict:
    Two exams on the same date with different time slots (e.g. MORNING vs EVENING)
    must still be detected as a conflict by every constraint class.  One test per
    constraint (6 constraints covered).

  Group B - unit, regression, date-only mode unaffected:
    The identical scenario using plain date assignments (no ExamPlacement / no
    time_slot) must behave exactly as before room scheduling was introduced.
    One test per constraint (6 constraints covered).

  Group C - integration, solver output:
    Runs the full BacktrackingSolver end-to-end and inspects every produced
    schedule to confirm that conflicting courses never share a date.

    - Room scheduling mode: the solver sees 3 time slots x 2 dates = 6 ExamBlock
      options per course.  If conflict logic incorrectly used date+time_slot, it
      could assign c1 to Jan 5 MORNING and c2 to Jan 5 EVENING.  The test asserts
      that never happens across all produced schedules.

    - Date-only regression: the same two courses, same period, no room scheduling.
      Verifies legacy solver behavior is completely unaffected.
"""

from datetime import date

from src.models.exam_placement import ExamPlacement
from src.models.enums import TimeSlot, Semester, Moed, ReqType
from src.models.room import Room
from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.program_requirement import ProgramRequirement
from src.models.constraint_settings import ConstraintSettings
from src.models.enums import Evaluation

from tests.algorithm.constraint_helpers import (
    make_elective_course,
    make_obligatory_course,
    make_schedule,
)

from src.algorithm.constraints.collision_constraint import CollisionConstraint
from src.algorithm.constraints.mandatory_gap_constraint import MandatoryGapConstraint
from src.algorithm.constraints.all_gap_constraint import AllGapConstraint
from src.algorithm.constraints.partial_collision_constraint import PartialCollisionConstraint
from src.algorithm.constraints.partial_mandatory_gap_constraint import PartialMandatoryGapConstraint
from src.algorithm.constraints.partial_all_gap_constraint import PartialAllGapConstraint

from src.algorithm.backtracking_solver import BacktrackingSolver
from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.basic_version_validator import BasicVersionValidator
from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.course_ordering_heuristic import CourseOrderingHeuristic
from src.algorithm.forward_checker import ForwardChecker
from src.algorithm.scheduling_mode_factory import SchedulingModeFactory


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_ROOM = Room("R1", "BuildingA", 30)
_DATE = date(2026, 1, 10)


def _placement(time_slot: TimeSlot) -> ExamPlacement:
    """Return a room-based placement on _DATE in the given slot."""
    return ExamPlacement(date=_DATE, time_slot=time_slot, rooms=(_ROOM,))


# ---------------------------------------------------------------------------
# Group A: same date, different time slots — conflict must still be detected
# ---------------------------------------------------------------------------

def test_collision_constraint_rejects_same_date_different_time_slots():
    """Two electives for the same program on the same date must conflict even with different slots."""
    constraint = CollisionConstraint(k=0)
    e1 = make_elective_course("E1", "83101")
    e2 = make_elective_course("E2", "83101")
    sched = make_schedule(
        (e1, _placement(TimeSlot.MORNING)),
        (e2, _placement(TimeSlot.EVENING)),
    )
    assert constraint.is_satisfied(sched) is False


def test_mandatory_gap_rejects_same_date_different_time_slots():
    """Two obligatory exams for the same cohort on the same date must conflict even with different slots."""
    constraint = MandatoryGapConstraint(k=1)
    o1 = make_obligatory_course("O1", "83101")
    o2 = make_obligatory_course("O2", "83101")
    sched = make_schedule(
        (o1, _placement(TimeSlot.MORNING)),
        (o2, _placement(TimeSlot.EVENING)),
    )
    assert constraint.is_satisfied(sched) is False


def test_all_gap_rejects_same_date_different_time_slots():
    """Two exams for the same cohort on the same date must conflict even with different slots."""
    constraint = AllGapConstraint(k=1)
    c1 = make_obligatory_course("C1", "83101")
    c2 = make_elective_course("C2", "83101")
    sched = make_schedule(
        (c1, _placement(TimeSlot.MORNING)),
        (c2, _placement(TimeSlot.AFTERNOON)),
    )
    assert constraint.is_satisfied(sched) is False


def test_partial_collision_rejects_same_date_different_time_slots():
    """PartialCollisionConstraint must detect a same-date conflict regardless of time slot."""
    constraint = PartialCollisionConstraint(k=0)
    e1 = make_elective_course("E1", "83101")
    e2 = make_elective_course("E2", "83101")
    sched = make_schedule(
        (e1, _placement(TimeSlot.MORNING)),
        (e2, _placement(TimeSlot.EVENING)),
    )
    assert constraint.is_still_valid(sched) is False


def test_partial_mandatory_gap_rejects_same_date_different_time_slots():
    """PartialMandatoryGapConstraint must detect a same-date conflict regardless of time slot."""
    constraint = PartialMandatoryGapConstraint(k=1)
    o1 = make_obligatory_course("O1", "83101")
    o2 = make_obligatory_course("O2", "83101")
    sched = make_schedule(
        (o1, _placement(TimeSlot.MORNING)),
        (o2, _placement(TimeSlot.EVENING)),
    )
    assert constraint.is_still_valid(sched) is False


def test_partial_all_gap_rejects_same_date_different_time_slots():
    """PartialAllGapConstraint must detect a same-date conflict regardless of time slot."""
    constraint = PartialAllGapConstraint(k=1)
    c1 = make_obligatory_course("C1", "83101")
    c2 = make_elective_course("C2", "83101")
    sched = make_schedule(
        (c1, _placement(TimeSlot.MORNING)),
        (c2, _placement(TimeSlot.AFTERNOON)),
    )
    assert constraint.is_still_valid(sched) is False


# ---------------------------------------------------------------------------
# Group B: regression — date-only assignments still conflict exactly as before
# ---------------------------------------------------------------------------

def test_collision_constraint_rejects_same_date_no_time_slot():
    """Date-only collision behavior is unaffected by the room scheduling feature."""
    constraint = CollisionConstraint(k=0)
    e1 = make_elective_course("E1", "83101")
    e2 = make_elective_course("E2", "83101")
    sched = make_schedule(
        (e1, _DATE),
        (e2, _DATE),
    )
    assert constraint.is_satisfied(sched) is False


def test_mandatory_gap_rejects_same_date_no_time_slot():
    """Date-only mandatory gap behavior is unaffected by the room scheduling feature."""
    constraint = MandatoryGapConstraint(k=1)
    o1 = make_obligatory_course("O1", "83101")
    o2 = make_obligatory_course("O2", "83101")
    sched = make_schedule(
        (o1, _DATE),
        (o2, _DATE),
    )
    assert constraint.is_satisfied(sched) is False


def test_all_gap_rejects_same_date_no_time_slot():
    """Date-only all-gap behavior is unaffected by the room scheduling feature."""
    constraint = AllGapConstraint(k=1)
    c1 = make_obligatory_course("C1", "83101")
    c2 = make_elective_course("C2", "83101")
    sched = make_schedule(
        (c1, _DATE),
        (c2, _DATE),
    )
    assert constraint.is_satisfied(sched) is False


def test_partial_collision_rejects_same_date_no_time_slot():
    """Date-only partial collision behavior is unaffected by the room scheduling feature."""
    constraint = PartialCollisionConstraint(k=0)
    e1 = make_elective_course("E1", "83101")
    e2 = make_elective_course("E2", "83101")
    sched = make_schedule(
        (e1, _DATE),
        (e2, _DATE),
    )
    assert constraint.is_still_valid(sched) is False


def test_partial_mandatory_gap_rejects_same_date_no_time_slot():
    """Date-only partial mandatory gap behavior is unaffected by the room scheduling feature."""
    constraint = PartialMandatoryGapConstraint(k=1)
    o1 = make_obligatory_course("O1", "83101")
    o2 = make_obligatory_course("O2", "83101")
    sched = make_schedule(
        (o1, _DATE),
        (o2, _DATE),
    )
    assert constraint.is_still_valid(sched) is False


def test_partial_all_gap_rejects_same_date_no_time_slot():
    """Date-only partial all-gap behavior is unaffected by the room scheduling feature."""
    constraint = PartialAllGapConstraint(k=1)
    c1 = make_obligatory_course("C1", "83101")
    c2 = make_elective_course("C2", "83101")
    sched = make_schedule(
        (c1, _DATE),
        (c2, _DATE),
    )
    assert constraint.is_still_valid(sched) is False


# ---------------------------------------------------------------------------
# Integration helpers
# ---------------------------------------------------------------------------

def _make_conflicting_courses(num_students: int = 10):
    """Return two obligatory courses that share the same cohort (program + year)."""
    c1 = Course("Math", "C1", "Prof", Evaluation.Exam, num_students)
    c1.add_requirement(ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory))

    c2 = Course("Physics", "C2", "Prof", Evaluation.Exam, num_students)
    c2.add_requirement(ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory))

    return c1, c2


def _make_solver(courses, programs, rooms=None):
    index = ConstraintIndex()
    index.build(courses, programs)
    collision_validator = BasicVersionValidator(index)
    validator = ConstraintValidator(index, collision_validator)
    heuristic = CourseOrderingHeuristic(index)
    checker = ForwardChecker(validator)

    if rooms is not None:
        components = SchedulingModeFactory.create(
            ConstraintSettings(room_scheduling_enabled=True),
            rooms,
        )
        solver = BacktrackingSolver(collision_validator, heuristic, checker, scheduling_components=components)
    else:
        solver = BacktrackingSolver(collision_validator, heuristic, checker)

    return solver, validator


# ---------------------------------------------------------------------------
# Group C: integration - solver never places conflicting courses on the same date
# ---------------------------------------------------------------------------

def test_room_mode_solver_never_places_conflicting_courses_on_same_date():
    """
    Integration: in room scheduling mode the solver must not assign two conflicting
    courses to the same date even though 3 time slots per day are available.

    Setup:
      - Two obligatory courses that share the same cohort (program 83101, year 1),
        so the solver knows they conflict.
      - A period with 2 available dates (Jan 5 and Jan 10).
      - Room scheduling enabled: each date expands into 3 ExamBlocks
        (MORNING / AFTERNOON / EVENING), giving 6 options per course.

    The bug this guards against:
      If conflict detection were at the date+time_slot level instead of the date
      level, the solver could treat Jan 5 MORNING and Jan 5 EVENING as non-
      conflicting slots and assign c1 to one and c2 to the other — placing two
      exams a student must sit on the same calendar day.

    What we assert:
      Every schedule the solver produces must have c1 and c2 on different dates.
      The time slots they were assigned do not matter; the dates must differ.
    """
    c1, c2 = _make_conflicting_courses(num_students=10)
    rooms = [Room("R1", "A", 30)]
    solver, validator = _make_solver([c1, c2], ["83101"], rooms=rooms)

    period = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "10-01-2026")
    period.possible_dates = [date(2026, 1, 5), date(2026, 1, 10)]

    schedules = solver.solve([c1, c2], period, validator)

    assert len(schedules) > 0, "Solver must find at least one valid schedule"
    for schedule in schedules:
        placements = schedule.placements
        assert placements[c1].date != placements[c2].date, (
            f"Conflicting courses must never share a date; "
            f"c1={placements[c1].date} c2={placements[c2].date}"
        )


def test_date_only_mode_solver_never_places_conflicting_courses_on_same_date():
    """
    Regression: in legacy date-only mode the solver must behave exactly as before —
    conflicting courses are never assigned to the same date.

    Setup:
      - The same two conflicting obligatory courses and the same 2-date period as
        the room mode test, but with room scheduling disabled (date-only mode).
      - No ExamPlacement or time slots are involved; the solver assigns raw dates.

    What we assert:
      Every schedule the solver produces must have c1 and c2 on different dates,
      confirming that introducing room scheduling did not change the date-only
      conflict behavior in any way.
    """
    c1, c2 = _make_conflicting_courses(num_students=0)
    solver, validator = _make_solver([c1, c2], ["83101"])

    period = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "10-01-2026")
    period.possible_dates = [date(2026, 1, 5), date(2026, 1, 10)]

    schedules = solver.solve([c1, c2], period, validator)

    assert len(schedules) > 0, "Solver must find at least one valid schedule"
    for schedule in schedules:
        assignments = schedule.assignments
        assert assignments[c1] != assignments[c2], (
            f"Conflicting courses must never share a date; "
            f"c1={assignments[c1]} c2={assignments[c2]}"
        )
