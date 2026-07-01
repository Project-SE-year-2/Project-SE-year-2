"""
EP-169 — automated tests for the *existing* manual schedule-editing flow.

The app already exposes manual editing through the IAppService contract:

    AppService.validate_manual_move(period_id, exam_rows, moving_exam, target_date)
        -> delegates to ManualMoveValidator and returns [{rule, reason}, ...]
    AppService.save_manual_edit(period_id, index, edited_rows)
        -> persists the edited rows (batch file + scores.db when disk-based) and
           records an in-memory override that get_period_schedule() serves first.

These tests target that shipped flow — not a parallel implementation. The
ManualMoveValidator rule maths is covered directly by test_manual_move_validator;
here we verify the AppService wrapper (period lookup, delegation, dict shape) and
the save/override round-trip.

DataStore disk I/O is patched out so the tests never touch real files.
"""

from datetime import date

import pytest

from src.presenter.app_service import AppService
from src.presenter.data_store import DataStore
from src.models.constraint_settings import ConstraintSettings


@pytest.fixture(autouse=True)
def reset_singleton():
    AppService._instance = None
    yield
    AppService._instance = None


def _make_service(monkeypatch) -> AppService:
    monkeypatch.setattr(DataStore, "load", lambda self: False)
    monkeypatch.setattr(DataStore, "save", lambda self: None)
    return AppService()


def _period(forbidden=None):
    """A period dict shaped like get_periods() output (Jan 2026, no allow-list)."""
    return {
        "id": "FALL_Aleph",
        "semester": "FALL",
        "moed": "Aleph",
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 1, 31),
        "allowed_days": [],
        "forbidden_days": list(forbidden or []),
    }


def _row(cid, name, exam_date, req_type="Obligatory", programs=("83101",)):
    return {
        "course_number": cid,
        "course_name": name,
        "type": req_type,
        "programs": list(programs),
        "exam_date": exam_date,
    }


class _FakeIndex:
    """Minimal ConstraintIndex stand-in: the given id pair always collides."""

    def __init__(self, colliding_pair):
        self._pair = set(colliding_pair)

    def do_collide_by_id(self, a, b):
        return {a, b} == self._pair


# ---------------------------------------------------------------------------
# validate_manual_move — the AppService wrapper
# ---------------------------------------------------------------------------

def test_unknown_period_reports_period_not_found(monkeypatch):
    svc = _make_service(monkeypatch)
    monkeypatch.setattr(svc, "get_periods", lambda: [])   # no periods at all
    errors = svc.validate_manual_move(
        "FALL_Aleph", [], _row("C1", "Physics", date(2026, 1, 5)), date(2026, 1, 6)
    )
    assert len(errors) == 1
    assert errors[0]["rule"] == "period_not_found"


def test_valid_move_returns_no_errors(monkeypatch):
    svc = _make_service(monkeypatch)
    monkeypatch.setattr(svc, "get_periods", lambda: [_period()])
    moving = _row("C1", "Physics", date(2026, 1, 5))
    others = [_row("C2", "Algebra", date(2026, 1, 20))]
    errors = svc.validate_manual_move("FALL_Aleph", [moving] + others, moving, date(2026, 1, 10))
    assert errors == []


def test_move_outside_period_range_is_rejected(monkeypatch):
    svc = _make_service(monkeypatch)
    monkeypatch.setattr(svc, "get_periods", lambda: [_period()])
    moving = _row("C1", "Physics", date(2026, 1, 5))
    errors = svc.validate_manual_move("FALL_Aleph", [moving], moving, date(2026, 2, 15))
    assert any(e["rule"] == "period_bounds" for e in errors)


def test_move_to_forbidden_date_is_rejected(monkeypatch):
    svc = _make_service(monkeypatch)
    forbidden = date(2026, 1, 12)
    monkeypatch.setattr(svc, "get_periods", lambda: [_period(forbidden=[forbidden])])
    moving = _row("C1", "Physics", date(2026, 1, 5))
    errors = svc.validate_manual_move("FALL_Aleph", [moving], moving, forbidden)
    assert any(e["rule"] == "forbidden_date" for e in errors)


def test_same_day_obligatory_collision_is_rejected(monkeypatch):
    svc = _make_service(monkeypatch)
    monkeypatch.setattr(svc, "get_periods", lambda: [_period()])
    svc._constraint_index = _FakeIndex({"C1", "C2"})
    moving = _row("C1", "Physics", date(2026, 1, 5))
    other = _row("C2", "Algebra", date(2026, 1, 10))
    errors = svc.validate_manual_move("FALL_Aleph", [moving, other], moving, date(2026, 1, 10))
    assert any(e["rule"] == "collision" for e in errors)


def test_daily_cap_setting_is_enforced_by_wrapper(monkeypatch):
    svc = _make_service(monkeypatch)
    monkeypatch.setattr(svc, "get_periods", lambda: [_period()])
    svc._constraint_settings = ConstraintSettings(daily_cap_enabled=True, daily_cap_k=1)
    moving = _row("C1", "Physics", date(2026, 1, 5))
    other = _row("C2", "Algebra", date(2026, 1, 10))   # already on the target day
    errors = svc.validate_manual_move("FALL_Aleph", [moving, other], moving, date(2026, 1, 10))
    assert any(e["rule"] == "daily_cap" for e in errors)


def test_errors_are_dicts_with_rule_and_reason(monkeypatch):
    svc = _make_service(monkeypatch)
    monkeypatch.setattr(svc, "get_periods", lambda: [_period()])
    moving = _row("C1", "Physics", date(2026, 1, 5))
    errors = svc.validate_manual_move("FALL_Aleph", [moving], moving, date(2026, 3, 1))
    assert errors and all({"rule", "reason"} <= set(e) for e in errors)


# ---------------------------------------------------------------------------
# save_manual_edit — persistence + get_period_schedule override round-trip
# ---------------------------------------------------------------------------

def test_saved_edit_is_served_by_get_period_schedule(monkeypatch):
    svc = _make_service(monkeypatch)
    edited = [_row("C1", "Physics", date(2026, 1, 9))]

    svc.save_manual_edit("FALL_Aleph", 0, edited)

    assert svc.get_period_schedule("FALL_Aleph", 0) == edited


def test_override_only_affects_the_saved_index(monkeypatch):
    svc = _make_service(monkeypatch)
    edited = [_row("C1", "Physics", date(2026, 1, 9))]
    svc.save_manual_edit("FALL_Aleph", 2, edited)

    # A different index has no override → falls through (no data → empty list).
    assert svc.get_period_schedule("FALL_Aleph", 0) == []


def test_saved_override_is_a_deep_copy(monkeypatch):
    svc = _make_service(monkeypatch)
    edited = [_row("C1", "Physics", date(2026, 1, 9))]
    svc.save_manual_edit("FALL_Aleph", 0, edited)

    edited[0]["exam_date"] = date(2026, 1, 30)          # mutate the caller's list
    served = svc.get_period_schedule("FALL_Aleph", 0)
    assert served[0]["exam_date"] == date(2026, 1, 9)   # stored copy is untouched


def test_save_closes_open_ranking_engine(monkeypatch):
    svc = _make_service(monkeypatch)

    class _Eng:
        closed = False
        def close(self):
            self.closed = True

    eng = _Eng()
    svc._ranking_engine = eng
    svc.save_manual_edit("FALL_Aleph", 0, [_row("C1", "Physics", date(2026, 1, 9))])

    assert eng.closed is True
    assert svc._ranking_engine is None
