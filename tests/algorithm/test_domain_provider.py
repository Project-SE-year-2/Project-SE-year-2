"""
Tests for the SchedulingDomainProvider interface and its two concrete implementations:
  - DateOnlyDomainProvider        — returns date objects filtered by collision constraints
  - RoomSchedulingDomainProvider  — returns ExamBlock(date, time_slot) objects

Key invariant verified throughout: neither provider inspects room_scheduling_enabled
directly.  Mode selection is the sole responsibility of SchedulingModeFactory.
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
    RoomPlacementFactory,
    RoomSchedulingDomainProvider,
    SchedulingModeFactory,
)
from src.models.constraint_settings import ConstraintSettings
from src.models.course import Course
from src.models.enums import Evaluation, Moed, Semester, TimeSlot
from src.models.exam_block import ExamBlock
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
    # RoomSchedulingDomainProvider no longer needs a RoomAllocator — rooms are
    # allocated later by RoomPlacementFactory.
    provider = RoomSchedulingDomainProvider()
    assert hasattr(provider, "candidates_for")


def test_providers_are_distinct_classes():
    # Ensures each mode uses its own class — not a single conditional branch.
    assert type(DateOnlyDomainProvider()) is not type(RoomSchedulingDomainProvider())


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
    index.build([c1, c2], ["P1"])
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
    candidates = provider.candidates_for(_course(), _partial(period), period, _validator())
    assert isinstance(candidates, list)


# ---------------------------------------------------------------------------
# RoomSchedulingDomainProvider — returned values are ExamBlock objects
# ---------------------------------------------------------------------------

def test_room_provider_returns_exam_blocks_not_placements():
    """
    RoomSchedulingDomainProvider must return ExamBlock objects (pure domain values).
    Room allocation is the responsibility of RoomPlacementFactory, not the provider.
    """
    provider = RoomSchedulingDomainProvider()
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 5), date(2026, 1, 5))
    period.possible_dates = [date(2026, 1, 5)]

    candidates = provider.candidates_for(_course(students=10), _partial(period), period, _validator())

    assert all(isinstance(c, ExamBlock) for c in candidates)
    assert not any(isinstance(c, ExamPlacement) for c in candidates)


def test_room_provider_generates_one_block_per_time_slot_per_date():
    """With one available date, the provider generates one ExamBlock per TimeSlot."""
    provider = RoomSchedulingDomainProvider()
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 5), date(2026, 1, 5))
    period.possible_dates = [date(2026, 1, 5)]

    candidates = provider.candidates_for(_course(students=10), _partial(period), period, _validator())

    assert len(candidates) == len(list(TimeSlot))
    slots_returned = {c.time_slot for c in candidates}
    assert slots_returned == set(TimeSlot)


def test_room_provider_blocks_contain_correct_date():
    """Every ExamBlock must carry the date it was generated for."""
    provider = RoomSchedulingDomainProvider()
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 5), date(2026, 1, 5))
    period.possible_dates = [date(2026, 1, 5)]

    candidates = provider.candidates_for(_course(students=10), _partial(period), period, _validator())

    assert all(c.date == date(2026, 1, 5) for c in candidates)


def test_room_provider_blocks_contain_no_room_data():
    """
    ExamBlock objects must NOT carry room information — that belongs to
    RoomPlacementFactory.  Verifies the single-responsibility separation.
    """
    provider = RoomSchedulingDomainProvider()
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 5), date(2026, 1, 5))
    period.possible_dates = [date(2026, 1, 5)]

    candidates = provider.candidates_for(_course(students=10), _partial(period), period, _validator())

    # ExamBlock has only date and time_slot — no rooms attribute.
    for block in candidates:
        assert not hasattr(block, "rooms")
        assert not hasattr(block, "total_capacity")


def test_room_provider_returns_multiple_dates_when_available():
    """Provider generates ExamBlock candidates for every available date."""
    provider = RoomSchedulingDomainProvider()
    period = _period(date(2026, 1, 5), date(2026, 1, 6))

    candidates = provider.candidates_for(_course(students=10), _partial(period), period, _validator())

    dates_in_candidates = {c.date for c in candidates}
    assert date(2026, 1, 5) in dates_in_candidates
    assert date(2026, 1, 6) in dates_in_candidates


def test_room_provider_does_not_inspect_room_scheduling_enabled():
    # Provider receives no ConstraintSettings — must not raise or import the flag.
    provider = RoomSchedulingDomainProvider()
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 5), date(2026, 1, 5))
    period.possible_dates = [date(2026, 1, 5)]

    candidates = provider.candidates_for(_course(students=10), _partial(period), period, _validator())

    assert isinstance(candidates, list)


def test_room_provider_requires_no_room_allocator():
    """
    RoomSchedulingDomainProvider must be constructible without a RoomAllocator.
    Room allocation responsibility belongs exclusively to RoomPlacementFactory.
    """
    # This must not raise — no allocator argument needed.
    provider = RoomSchedulingDomainProvider()
    assert provider is not None


# ---------------------------------------------------------------------------
# RoomPlacementFactory — converts ExamBlock → ExamPlacement with rooms
# ---------------------------------------------------------------------------

def test_room_placement_factory_converts_block_to_placement():
    """RoomPlacementFactory must return an ExamPlacement for a valid ExamBlock."""
    allocator = RoomAllocator([Room("101", "1", 50)])
    factory = RoomPlacementFactory(allocator)
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 5), date(2026, 1, 5))
    block = ExamBlock(date(2026, 1, 5), TimeSlot.MORNING)

    result = factory.create(block, _course(students=10), _partial(period))

    assert isinstance(result, ExamPlacement)
    assert result.date == date(2026, 1, 5)
    assert result.time_slot == TimeSlot.MORNING
    assert len(result.rooms) > 0


def test_room_placement_factory_returns_none_when_no_rooms_available():
    """
    Factory returns None when RoomAllocator cannot satisfy the course capacity,
    allowing the solver to skip this candidate without pruning the whole branch.
    """
    allocator = RoomAllocator([Room("101", "1", 5)])
    factory = RoomPlacementFactory(allocator)
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 5), date(2026, 1, 5))
    block = ExamBlock(date(2026, 1, 5), TimeSlot.MORNING)

    result = factory.create(block, _course(students=200), _partial(period))

    assert result is None


def test_room_placement_factory_respects_occupied_rooms():
    """
    When a room is already used for the same date+slot in the partial schedule,
    the factory must not assign it again.
    """
    room = Room("101", "1", 50)
    allocator = RoomAllocator([room])
    factory = RoomPlacementFactory(allocator)
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 5), date(2026, 1, 5))
    period.possible_dates = [date(2026, 1, 5)]

    # Block the only room in MORNING for another course.
    partial = _partial(period)
    blocker = _course("BLOCKER", students=10)
    partial.assign(blocker, ExamPlacement(date(2026, 1, 5), TimeSlot.MORNING, (room,)))

    block = ExamBlock(date(2026, 1, 5), TimeSlot.MORNING)
    result = factory.create(block, _course(students=10), partial)

    # No rooms left for MORNING — factory must return None.
    assert result is None


# ---------------------------------------------------------------------------
# Factory wires correct provider and factory per mode
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


def test_factory_room_mode_injects_room_placement_factory():
    """RoomPlacementFactory (not the domain provider) must own the RoomAllocator."""
    components = SchedulingModeFactory.create(
        ConstraintSettings(room_scheduling_enabled=True),
        [Room("101", "1", 50)],
    )
    assert isinstance(components.placement_factory, RoomPlacementFactory)


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
