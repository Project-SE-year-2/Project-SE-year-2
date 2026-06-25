"""
Tests for the SchedulingDomainProvider interface and its two concrete implementations:
  - DateOnlyDomainProvider   — returns available dates filtered by collision constraints
  - RoomSchedulingDomainProvider — returns full ExamPlacement objects (date + slot + rooms)

Both providers must satisfy the DomainProvider Protocol and must NOT inspect
room_scheduling_enabled directly.  Mode selection is the sole responsibility
of SchedulingModeFactory.
"""

from datetime import date

import pytest

from src.algorithm.basic_version_validator import BasicVersionValidator
from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.scheduling_mode_factory import (
    DateOnlyDomainProvider,
    DomainProvider,
    RoomAllocator,
    RoomSchedulingDomainProvider,
    SchedulingModeFactory,
)
from src.models.constraint_settings import ConstraintSettings
from src.models.course import Course
from src.models.enums import Evaluation, Moed, Semester, TimeSlot
from src.models.exam_period import ExamPeriod
from src.models.exam_placement import ExamPlacement
from src.models.exam_schedule import ExamSchedule
from src.models.room import Room


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _validator() -> ConstraintValidator:
    """Build a no-constraint ConstraintValidator (no programs, no courses)."""
    index = ConstraintIndex()
    index.build([], [])
    return ConstraintValidator(index, BasicVersionValidator(index))


def _period(start: date = date(2026, 1, 5), end: date = date(2026, 1, 7)) -> ExamPeriod:
    """Create a period with three available dates by default."""
    return ExamPeriod(Semester.FALL, Moed.Aleph, start, end)


def _course(course_id: str = "C1", students: int = 20) -> Course:
    return Course(f"Course {course_id}", course_id, "Prof", Evaluation.Exam, students)


def _partial(period: ExamPeriod) -> ExamSchedule:
    return ExamSchedule(period)


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

def test_date_only_provider_satisfies_domain_provider_protocol():
    # The Protocol is structural — an instance must have candidates_for().
    provider = DateOnlyDomainProvider()
    assert hasattr(provider, "candidates_for")


def test_room_scheduling_provider_satisfies_domain_provider_protocol():
    allocator = RoomAllocator([Room("101", "1", 50)])
    provider = RoomSchedulingDomainProvider(allocator)
    assert hasattr(provider, "candidates_for")


def test_providers_are_distinct_classes():
    # Ensures each mode uses its own class — not a single conditional branch.
    allocator = RoomAllocator([Room("101", "1", 50)])
    assert type(DateOnlyDomainProvider()) is not type(RoomSchedulingDomainProvider(allocator))


# ---------------------------------------------------------------------------
# DateOnlyDomainProvider — returned values are dates
# ---------------------------------------------------------------------------

def test_date_only_returns_dates_not_placements():
    provider = DateOnlyDomainProvider()
    period = _period()
    candidates = provider.candidates_for(_course(), _partial(period), period, _validator())

    assert all(isinstance(c, date) for c in candidates)


def test_date_only_returns_all_available_dates_when_no_conflicts():
    provider = DateOnlyDomainProvider()
    period = _period(date(2026, 1, 5), date(2026, 1, 7))
    candidates = provider.candidates_for(_course(), _partial(period), period, _validator())

    assert candidates == period.getAvailableDates()


def test_date_only_empty_period_returns_empty_list():
    # Mark the only available date as forbidden so getAvailableDates() returns [].
    provider = DateOnlyDomainProvider()
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 5), date(2026, 1, 5))
    period.possible_dates = [date(2026, 1, 5)]
    period.forbidden_days = [date(2026, 1, 5)]
    candidates = provider.candidates_for(_course(), _partial(period), period, _validator())

    assert candidates == []


def test_date_only_filters_out_conflicting_date():
    """A date already used by a colliding course must be excluded."""
    from src.models.program_requirement import ProgramRequirement
    from src.models.enums import ReqType

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 5), date(2026, 1, 5))
    period.possible_dates = [date(2026, 1, 5)]

    c1 = _course("C1")
    c2 = _course("C2")
    # program_id must be registered in index.build() programs list for collision detection.
    req = ProgramRequirement("P1", 1, Semester.FALL, ReqType.Obligatory)
    c1.add_requirement(req)
    c2.add_requirement(req)

    index = ConstraintIndex()
    index.build([c1, c2], ["P1"])   # "P1" must be in the programs list
    validator = ConstraintValidator(index, BasicVersionValidator(index))

    partial = _partial(period)
    partial.assign(c1, date(2026, 1, 5))

    provider = DateOnlyDomainProvider()
    candidates = provider.candidates_for(c2, partial, period, validator)

    assert candidates == []


def test_date_only_does_not_inspect_room_scheduling_enabled():
    # Provider must work without any ConstraintSettings — confirming it is mode-agnostic.
    provider = DateOnlyDomainProvider()
    period = _period(date(2026, 1, 5), date(2026, 1, 5))
    # No settings object anywhere in the call — must not raise.
    candidates = provider.candidates_for(_course(), _partial(period), period, _validator())
    assert isinstance(candidates, list)


# ---------------------------------------------------------------------------
# RoomSchedulingDomainProvider — returned values are ExamPlacements
# ---------------------------------------------------------------------------

def test_room_provider_returns_exam_placements():
    allocator = RoomAllocator([Room("101", "1", 50)])
    provider = RoomSchedulingDomainProvider(allocator)
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 5), date(2026, 1, 5))
    period.possible_dates = [date(2026, 1, 5)]

    candidates = provider.candidates_for(_course(students=10), _partial(period), period, _validator())

    assert all(isinstance(c, ExamPlacement) for c in candidates)


def test_room_provider_generates_one_candidate_per_time_slot():
    """With one available date, there must be one candidate per TimeSlot."""
    room = Room("101", "1", 50)
    allocator = RoomAllocator([room])
    provider = RoomSchedulingDomainProvider(allocator)
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 5), date(2026, 1, 5))
    period.possible_dates = [date(2026, 1, 5)]

    candidates = provider.candidates_for(_course(students=10), _partial(period), period, _validator())

    assert len(candidates) == len(list(TimeSlot))
    slots_returned = {c.time_slot for c in candidates}
    assert slots_returned == set(TimeSlot)


def test_room_provider_candidates_include_allocated_rooms():
    room = Room("A101", "A", 60)
    allocator = RoomAllocator([room])
    provider = RoomSchedulingDomainProvider(allocator)
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 5), date(2026, 1, 5))
    period.possible_dates = [date(2026, 1, 5)]

    candidates = provider.candidates_for(_course(students=50), _partial(period), period, _validator())

    assert all(c.rooms == (room,) for c in candidates)


def test_room_provider_excludes_slot_when_room_unavailable():
    """If the only room is taken in MORNING, that slot must not appear in candidates."""
    room = Room("101", "1", 50)
    allocator = RoomAllocator([room])
    provider = RoomSchedulingDomainProvider(allocator)

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 5), date(2026, 1, 5))
    period.possible_dates = [date(2026, 1, 5)]

    partial = _partial(period)
    blocking_course = _course("C_BLOCKER", students=10)
    blocking_placement = ExamPlacement(date(2026, 1, 5), TimeSlot.MORNING, (room,))
    partial.assign(blocking_course, blocking_placement)

    candidates = provider.candidates_for(_course(students=10), partial, period, _validator())

    returned_slots = {c.time_slot for c in candidates}
    assert TimeSlot.MORNING not in returned_slots


def test_room_provider_returns_multiple_dates_when_available():
    room = Room("101", "1", 50)
    allocator = RoomAllocator([room])
    provider = RoomSchedulingDomainProvider(allocator)
    period = _period(date(2026, 1, 5), date(2026, 1, 6))

    candidates = provider.candidates_for(_course(students=10), _partial(period), period, _validator())

    dates_in_candidates = {c.date for c in candidates}
    assert date(2026, 1, 5) in dates_in_candidates
    assert date(2026, 1, 6) in dates_in_candidates


def test_room_provider_returns_empty_when_no_rooms_can_satisfy_capacity():
    """A course requiring more students than total capacity yields no candidates."""
    room = Room("101", "1", 10)
    allocator = RoomAllocator([room])
    provider = RoomSchedulingDomainProvider(allocator)
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 5), date(2026, 1, 5))
    period.possible_dates = [date(2026, 1, 5)]

    candidates = provider.candidates_for(_course(students=200), _partial(period), period, _validator())

    assert candidates == []


def test_room_provider_does_not_inspect_room_scheduling_enabled():
    # Provider receives no ConstraintSettings — must not raise or import the flag.
    allocator = RoomAllocator([Room("101", "1", 50)])
    provider = RoomSchedulingDomainProvider(allocator)
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 5), date(2026, 1, 5))
    period.possible_dates = [date(2026, 1, 5)]

    candidates = provider.candidates_for(_course(students=10), _partial(period), period, _validator())

    assert isinstance(candidates, list)


# ---------------------------------------------------------------------------
# Factory wires the correct provider per mode (no direct flag inspection)
# ---------------------------------------------------------------------------

def test_factory_date_only_mode_injects_date_only_provider():
    components = SchedulingModeFactory.create(ConstraintSettings(room_scheduling_enabled=False))
    assert isinstance(components.domain_provider, DateOnlyDomainProvider)


def test_factory_room_mode_injects_room_scheduling_provider():
    components = SchedulingModeFactory.create(
        ConstraintSettings(room_scheduling_enabled=True),
        [Room("101", "1", 50)],
    )
    assert isinstance(components.domain_provider, RoomSchedulingDomainProvider)


def test_solver_receives_provider_not_settings_flag():
    """
    BacktrackingSolver must store domain_provider, not room_scheduling_enabled.
    Confirms the injection boundary: solver is mode-agnostic.
    """
    from src.algorithm.backtracking_solver import BacktrackingSolver
    from src.algorithm.basic_version_validator import BasicVersionValidator
    from src.algorithm.constraint_index import ConstraintIndex
    from src.algorithm.course_ordering_heuristic import CourseOrderingHeuristic
    from src.algorithm.forward_checker import ForwardChecker

    index = ConstraintIndex()
    index.build([], [])
    validator = BasicVersionValidator(index)
    cv = ConstraintValidator(index, validator)
    fc = ForwardChecker(cv)
    heuristic = CourseOrderingHeuristic(index)

    components = SchedulingModeFactory.create(ConstraintSettings(room_scheduling_enabled=False))
    solver = BacktrackingSolver(validator, heuristic, fc, scheduling_components=components)

    assert hasattr(solver, "_domain_provider")
    assert not hasattr(solver, "_room_scheduling_enabled")
