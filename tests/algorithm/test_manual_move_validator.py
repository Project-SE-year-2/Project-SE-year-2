"""
Tests for ManualMoveValidator (task 165).

Structure
---------
Each test group covers one validation rule in isolation.
A _FakeIndex stub replaces ConstraintIndex so these tests have
no dependency on the full solver stack.

Helper functions
----------------
_settings(**kwargs)  - build ConstraintSettings with all flags OFF by default
_period(...)         - build a period dict (start/end/forbidden/allowed)
_exam(...)           - build an exam row dict in the same format as get_period_schedule()
_FakeIndex           - minimal stub for do_collide_by_id / need_mandatory_gap / need_all_gap
"""

from datetime import date

import pytest

from src.algorithm.manual_move_validator import ManualMoveValidator, MoveValidationError
from src.models.constraint_settings import ConstraintSettings


# ── helpers ──────────────────────────────────────────────────────────────────

def _settings(**kwargs) -> ConstraintSettings:
    """Build ConstraintSettings with all constraint flags OFF by default."""
    defaults = dict(
        mandatory_gap_enabled=False, mandatory_gap_k=1,
        all_gap_enabled=False,       all_gap_k=1,
        elective_conflicts_enabled=False, elective_conflicts_k=0,
        daily_cap_enabled=False,     daily_cap_k=10,
        room_scheduling_enabled=False,
        spread_enabled=False,        spread_k=1,
    )
    defaults.update(kwargs)
    return ConstraintSettings(**defaults)


def _period(
    start=date(2026, 1, 1),
    end=date(2026, 1, 31),
    forbidden=None,
    allowed=None,
) -> dict:
    """Build a minimal period dict as returned by AppService.get_periods()."""
    return {
        "start_date":    start,
        "end_date":      end,
        "forbidden_days": forbidden or [],
        "allowed_days":   allowed or [],
    }


def _exam(
    course_number,
    course_name,
    exam_date,
    etype="Obligatory",
    programs=None,
    time_slot=None,
    room_ids=None,
) -> dict:
    """Build an exam row dict as returned by AppService.get_period_schedule()."""
    row = {
        "course_number": course_number,
        "course_name":   course_name,
        "exam_date":     exam_date,
        "type":          etype,
        "programs":      programs or ["CS"],
    }
    if time_slot is not None:
        row["time_slot"] = time_slot
        row["room_ids"]  = room_ids or []
    return row


class _FakeIndex:
    """
    Minimal ConstraintIndex stub.
    Pass the pairs you want to simulate as lists of (id_a, id_b) tuples.
    """

    def __init__(self, collision_pairs=None, mandatory_gap_pairs=None, all_gap_pairs=None):
        self._col  = set(tuple(sorted(p)) for p in (collision_pairs or []))
        self._mand = set(tuple(sorted(p)) for p in (mandatory_gap_pairs or []))
        self._all  = set(tuple(sorted(p)) for p in (all_gap_pairs or []))

    def do_collide_by_id(self, a, b):
        return tuple(sorted([a, b])) in self._col

    def need_mandatory_gap(self, a, b):
        return tuple(sorted([a, b])) in self._mand

    def need_all_gap(self, a, b):
        return tuple(sorted([a, b])) in self._all


VALIDATOR = ManualMoveValidator()


# ── period bounds ─────────────────────────────────────────────────────────────

class TestPeriodBounds:
    """Target date must fall inside the exam period's date range."""

    def test_before_start_is_rejected(self):
        exam = _exam("C1", "Math", date(2026, 1, 10))
        errors = VALIDATOR.validate([exam], exam, date(2025, 12, 31), _period(), _settings())
        assert len(errors) == 1
        assert errors[0].rule == "period_bounds"

    def test_after_end_is_rejected(self):
        exam = _exam("C1", "Math", date(2026, 1, 10))
        errors = VALIDATOR.validate([exam], exam, date(2026, 2, 1), _period(), _settings())
        assert len(errors) == 1
        assert errors[0].rule == "period_bounds"

    def test_within_range_is_valid(self):
        exam = _exam("C1", "Math", date(2026, 1, 10))
        errors = VALIDATOR.validate([exam], exam, date(2026, 1, 15), _period(), _settings())
        assert not any(e.rule == "period_bounds" for e in errors)

    def test_out_of_range_returns_early_no_other_checks(self):
        """When out of range, only the period_bounds error is returned."""
        exam = _exam("C1", "Math", date(2026, 1, 10))
        errors = VALIDATOR.validate(
            [exam], exam, date(2025, 12, 1),
            _period(forbidden=[date(2025, 12, 1)]),
            _settings(daily_cap_enabled=True, daily_cap_k=1),
        )
        assert len(errors) == 1
        assert errors[0].rule == "period_bounds"

    def test_allowed_days_list_respects_explicit_dates(self):
        """When allowed_days is populated, only those dates are valid."""
        allowed = [date(2026, 1, 5), date(2026, 1, 10), date(2026, 1, 15)]
        exam = _exam("C1", "Math", date(2026, 1, 5))
        # Valid: target is in the allowed list
        errors = VALIDATOR.validate([exam], exam, date(2026, 1, 10), _period(allowed=allowed), _settings())
        assert not any(e.rule == "period_bounds" for e in errors)
        # Invalid: target is in the range but not in the allowed list
        errors = VALIDATOR.validate([exam], exam, date(2026, 1, 7), _period(allowed=allowed), _settings())
        assert errors[0].rule == "period_bounds"


# ── forbidden date ────────────────────────────────────────────────────────────

class TestForbiddenDate:
    """Target date must not be in the period's forbidden_days list."""

    def test_forbidden_date_is_rejected(self):
        exam = _exam("C1", "Math", date(2026, 1, 10))
        errors = VALIDATOR.validate(
            [exam], exam, date(2026, 1, 15),
            _period(forbidden=[date(2026, 1, 15)]),
            _settings(),
        )
        assert any(e.rule == "forbidden_date" for e in errors)

    def test_non_forbidden_date_is_accepted(self):
        exam = _exam("C1", "Math", date(2026, 1, 10))
        errors = VALIDATOR.validate(
            [exam], exam, date(2026, 1, 14),
            _period(forbidden=[date(2026, 1, 15)]),
            _settings(),
        )
        assert not any(e.rule == "forbidden_date" for e in errors)


# ── basic collision ───────────────────────────────────────────────────────────

class TestBasicCollision:
    """
    v1.0 baseline rule: two courses in the same obligatory group
    (program_id, year, semester) cannot share a date.
    Uses ConstraintIndex.do_collide_by_id() when the index is available.
    """

    def test_collision_on_same_date_is_rejected(self):
        index  = _FakeIndex(collision_pairs=[("C1", "C2")])
        moving = _exam("C1", "Math", date(2026, 1, 10))
        other  = _exam("C2", "Physics", date(2026, 1, 15))
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 15), _period(), _settings(), index)
        assert any(e.rule == "collision" for e in errors)

    def test_no_shared_group_no_collision(self):
        index  = _FakeIndex(collision_pairs=[])
        moving = _exam("C1", "Math", date(2026, 1, 10))
        other  = _exam("C2", "Physics", date(2026, 1, 15))
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 15), _period(), _settings(), index)
        assert not any(e.rule == "collision" for e in errors)

    def test_colliding_courses_on_different_dates_is_valid(self):
        index  = _FakeIndex(collision_pairs=[("C1", "C2")])
        moving = _exam("C1", "Math", date(2026, 1, 10))
        other  = _exam("C2", "Physics", date(2026, 1, 15))
        # moving C1 to a date where C2 is not present
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 20), _period(), _settings(), index)
        assert not any(e.rule == "collision" for e in errors)

    def test_no_index_skips_collision_rather_than_false_positive(self):
        """Without an index we cannot determine collisions - skip instead of over-blocking."""
        moving = _exam("C1", "Math", date(2026, 1, 10), programs=["CS"])
        other  = _exam("C2", "Physics", date(2026, 1, 15), programs=["CS"])
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 15), _period(), _settings(), constraint_index=None)
        assert not any(e.rule == "collision" for e in errors)


# ── daily cap ─────────────────────────────────────────────────────────────────

class TestDailyCap:
    """Total exams on the target date must not exceed daily_cap_k."""

    def test_cap_exceeded_is_rejected(self):
        moving = _exam("C1", "Math", date(2026, 1, 1))
        others = [_exam(f"C{i}", f"Course{i}", date(2026, 1, 15)) for i in range(2, 5)]
        s = _settings(daily_cap_enabled=True, daily_cap_k=3)
        errors = VALIDATOR.validate([moving] + others, moving, date(2026, 1, 15), _period(), s)
        assert any(e.rule == "daily_cap" for e in errors)

    def test_exactly_at_cap_is_valid(self):
        moving = _exam("C1", "Math", date(2026, 1, 1))
        others = [_exam(f"C{i}", f"Course{i}", date(2026, 1, 15)) for i in range(2, 4)]
        s = _settings(daily_cap_enabled=True, daily_cap_k=3)
        errors = VALIDATOR.validate([moving] + others, moving, date(2026, 1, 15), _period(), s)
        assert not any(e.rule == "daily_cap" for e in errors)

    def test_cap_disabled_ignores_overflow(self):
        moving = _exam("C1", "Math", date(2026, 1, 1))
        others = [_exam(f"C{i}", f"Course{i}", date(2026, 1, 15)) for i in range(2, 20)]
        s = _settings(daily_cap_enabled=False, daily_cap_k=1)
        errors = VALIDATOR.validate([moving] + others, moving, date(2026, 1, 15), _period(), s)
        assert not any(e.rule == "daily_cap" for e in errors)


# ── mandatory gap ─────────────────────────────────────────────────────────────

class TestMandatoryGap:
    """
    Obligatory courses sharing the same (program_id, year) must be
    at least mandatory_gap_k days apart.
    Uses ConstraintIndex.need_mandatory_gap() for exact grouping.
    """

    def test_gap_violation_is_rejected(self):
        index  = _FakeIndex(mandatory_gap_pairs=[("C1", "C2")])
        moving = _exam("C1", "Math", date(2026, 1, 1))
        other  = _exam("C2", "Physics", date(2026, 1, 4))
        s = _settings(mandatory_gap_enabled=True, mandatory_gap_k=5)
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 2), _period(), s, index)
        assert any(e.rule == "mandatory_gap" for e in errors)

    def test_exact_k_gap_is_valid(self):
        index  = _FakeIndex(mandatory_gap_pairs=[("C1", "C2")])
        moving = _exam("C1", "Math", date(2026, 1, 1))
        other  = _exam("C2", "Physics", date(2026, 1, 6))
        s = _settings(mandatory_gap_enabled=True, mandatory_gap_k=5)
        # Moving C1 to Jan 1; C2 is on Jan 6 → gap = 5 = k → valid
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 1), _period(), s, index)
        assert not any(e.rule == "mandatory_gap" for e in errors)

    def test_no_shared_cohort_no_gap_error(self):
        index  = _FakeIndex(mandatory_gap_pairs=[])
        moving = _exam("C1", "Math", date(2026, 1, 1))
        other  = _exam("C2", "Physics", date(2026, 1, 2))
        s = _settings(mandatory_gap_enabled=True, mandatory_gap_k=10)
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 1), _period(), s, index)
        assert not any(e.rule == "mandatory_gap" for e in errors)

    def test_skipped_when_no_index(self):
        """Without a ConstraintIndex, gap checks are skipped to avoid false positives."""
        moving = _exam("C1", "Math", date(2026, 1, 1))
        other  = _exam("C2", "Physics", date(2026, 1, 2))
        s = _settings(mandatory_gap_enabled=True, mandatory_gap_k=10)
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 1), _period(), s, constraint_index=None)
        assert not any(e.rule == "mandatory_gap" for e in errors)


# ── all gap ───────────────────────────────────────────────────────────────────

class TestAllGap:
    """
    All courses (obligatory and elective) sharing (program_id, year)
    must be at least all_gap_k days apart.
    Uses ConstraintIndex.need_all_gap() for exact grouping.
    """

    def test_gap_violation_is_rejected(self):
        index  = _FakeIndex(all_gap_pairs=[("C1", "C2")])
        moving = _exam("C1", "Math", date(2026, 1, 1), etype="Elective")
        other  = _exam("C2", "Physics", date(2026, 1, 3), etype="Obligatory")
        s = _settings(all_gap_enabled=True, all_gap_k=5)
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 1), _period(), s, index)
        assert any(e.rule == "all_gap" for e in errors)

    def test_no_shared_cohort_no_gap_error(self):
        index  = _FakeIndex(all_gap_pairs=[])
        moving = _exam("C1", "Math", date(2026, 1, 1))
        other  = _exam("C2", "Physics", date(2026, 1, 2))
        s = _settings(all_gap_enabled=True, all_gap_k=10)
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 1), _period(), s, index)
        assert not any(e.rule == "all_gap" for e in errors)

    def test_skipped_when_no_index(self):
        moving = _exam("C1", "Math", date(2026, 1, 1))
        other  = _exam("C2", "Physics", date(2026, 1, 2))
        s = _settings(all_gap_enabled=True, all_gap_k=10)
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 1), _period(), s, constraint_index=None)
        assert not any(e.rule == "all_gap" for e in errors)


# ── elective collision ────────────────────────────────────────────────────────

class TestElectiveCollision:
    """
    Per-program daily elective count must not exceed elective_conflicts_k + 1.
    k=0 → at most 1 elective per program per day.
    k=1 → at most 2, etc.
    """

    def test_exceeds_limit_is_rejected(self):
        moving = _exam("C1", "Stats", date(2026, 1, 1), etype="Elective", programs=["CS"])
        other  = _exam("C2", "Logic", date(2026, 1, 15), etype="Elective", programs=["CS"])
        s = _settings(elective_conflicts_enabled=True, elective_conflicts_k=0)
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 15), _period(), s)
        assert any(e.rule == "elective_collision" for e in errors)

    def test_within_limit_is_valid(self):
        moving = _exam("C1", "Stats", date(2026, 1, 1), etype="Elective", programs=["CS"])
        other  = _exam("C2", "Logic", date(2026, 1, 15), etype="Elective", programs=["CS"])
        s = _settings(elective_conflicts_enabled=True, elective_conflicts_k=1)
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 15), _period(), s)
        assert not any(e.rule == "elective_collision" for e in errors)

    def test_obligatory_exam_not_checked(self):
        """The elective collision rule only applies when the moved exam is elective."""
        moving = _exam("C1", "Math", date(2026, 1, 1), etype="Obligatory", programs=["CS"])
        other  = _exam("C2", "Logic", date(2026, 1, 15), etype="Elective", programs=["CS"])
        s = _settings(elective_conflicts_enabled=True, elective_conflicts_k=0)
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 15), _period(), s)
        assert not any(e.rule == "elective_collision" for e in errors)

    def test_different_programs_not_counted_together(self):
        moving = _exam("C1", "Stats", date(2026, 1, 1), etype="Elective", programs=["CS"])
        other  = _exam("C2", "Logic", date(2026, 1, 15), etype="Elective", programs=["EE"])
        s = _settings(elective_conflicts_enabled=True, elective_conflicts_k=0)
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 15), _period(), s)
        assert not any(e.rule == "elective_collision" for e in errors)


# ── room scheduling ───────────────────────────────────────────────────────────

class TestRoomScheduling:
    """
    room_scheduling check: same (building, room_id, time_slot) on target_date → collision.

    room_ids in the dict are composite "building:room_id" strings, matching
    RoomAndSlotConstraint which keys rooms by (building, room_id, date, slot).
    Two rooms in different buildings with the same room number are distinct.
    """

    def test_same_building_same_room_same_slot_is_blocked(self):
        moving = _exam("C1", "Math",    date(2026, 1, 1),  time_slot="MORNING", room_ids=["B1:101"])
        other  = _exam("C2", "Physics", date(2026, 1, 15), time_slot="MORNING", room_ids=["B1:101"])
        s = _settings(room_scheduling_enabled=True)
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 15), _period(), s)
        assert any(e.rule == "room_scheduling" for e in errors)

    def test_different_building_same_room_number_same_slot_is_allowed(self):
        """B1/101 and B2/101 are different physical rooms — must not conflict."""
        moving = _exam("C1", "Math",    date(2026, 1, 1),  time_slot="MORNING", room_ids=["B1:101"])
        other  = _exam("C2", "Physics", date(2026, 1, 15), time_slot="MORNING", room_ids=["B2:101"])
        s = _settings(room_scheduling_enabled=True)
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 15), _period(), s)
        assert not any(e.rule == "room_scheduling" for e in errors)

    def test_same_room_different_slot_is_allowed(self):
        moving = _exam("C1", "Math",    date(2026, 1, 1),  time_slot="MORNING",   room_ids=["B1:101"])
        other  = _exam("C2", "Physics", date(2026, 1, 15), time_slot="AFTERNOON", room_ids=["B1:101"])
        s = _settings(room_scheduling_enabled=True)
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 15), _period(), s)
        assert not any(e.rule == "room_scheduling" for e in errors)

    def test_different_room_same_building_same_slot_is_allowed(self):
        moving = _exam("C1", "Math",    date(2026, 1, 1),  time_slot="MORNING", room_ids=["B1:101"])
        other  = _exam("C2", "Physics", date(2026, 1, 15), time_slot="MORNING", room_ids=["B1:202"])
        s = _settings(room_scheduling_enabled=True)
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 15), _period(), s)
        assert not any(e.rule == "room_scheduling" for e in errors)

    def test_collision_on_different_date_is_ignored(self):
        """An exam sharing room+slot NOT on target_date must not trigger an error."""
        moving = _exam("C1", "Math",    date(2026, 1, 1),  time_slot="MORNING", room_ids=["B1:101"])
        other  = _exam("C2", "Physics", date(2026, 1, 20), time_slot="MORNING", room_ids=["B1:101"])
        s = _settings(room_scheduling_enabled=True)
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 15), _period(), s)
        assert not any(e.rule == "room_scheduling" for e in errors)

    def test_no_room_data_on_moving_exam_skips_check(self):
        """If the moving exam has no time_slot/room_ids, skip (not a room-scheduled move)."""
        moving = _exam("C1", "Math",    date(2026, 1, 1))
        other  = _exam("C2", "Physics", date(2026, 1, 15), time_slot="MORNING", room_ids=["B1:101"])
        s = _settings(room_scheduling_enabled=True)
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 15), _period(), s)
        assert not any(e.rule == "room_scheduling" for e in errors)

    def test_room_scheduling_disabled_skips_check(self):
        moving = _exam("C1", "Math",    date(2026, 1, 1),  time_slot="MORNING", room_ids=["B1:101"])
        other  = _exam("C2", "Physics", date(2026, 1, 15), time_slot="MORNING", room_ids=["B1:101"])
        s = _settings(room_scheduling_enabled=False)
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 15), _period(), s)
        assert not any(e.rule == "room_scheduling" for e in errors)


# ── combined and edge cases ───────────────────────────────────────────────────

class TestCombinedAndEdgeCases:

    def test_multiple_errors_returned_together(self):
        """A move that is both forbidden and causes a collision returns both errors."""
        index  = _FakeIndex(collision_pairs=[("C1", "C2")])
        moving = _exam("C1", "Math", date(2026, 1, 1))
        other  = _exam("C2", "Physics", date(2026, 1, 15))
        period = _period(forbidden=[date(2026, 1, 15)])
        errors = VALIDATOR.validate([moving, other], moving, date(2026, 1, 15), period, _settings(), index)
        rules  = {e.rule for e in errors}
        assert "forbidden_date" in rules
        assert "collision" in rules

    def test_move_to_same_date_produces_no_errors(self):
        """Moving an exam to its current date should not introduce any new errors."""
        index  = _FakeIndex()
        moving = _exam("C1", "Math", date(2026, 1, 10))
        s      = _settings(daily_cap_enabled=True, daily_cap_k=5)
        errors = VALIDATOR.validate([moving], moving, date(2026, 1, 10), _period(), s, index)
        assert errors == []

    def test_errors_contain_human_readable_reason(self):
        """Every returned error must have a non-empty reason string."""
        exam   = _exam("C1", "Math", date(2026, 1, 10))
        errors = VALIDATOR.validate([exam], exam, date(2025, 12, 1), _period(), _settings())
        for e in errors:
            assert isinstance(e.reason, str) and len(e.reason) > 0