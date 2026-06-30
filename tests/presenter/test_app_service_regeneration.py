"""
EP-159 - Regeneration Flow & Result Reset Fixes.

These tests pin down the behaviour added/fixed in EP-159 on top of the
EP-149 dirty-flag skeleton:

  1. Selecting a *different* set of programs is an input change - it must
     clear the previous run's results and scores DB, not merely flag dirty.
  2. Every input mutator funnels through _invalidate_results(), which clears
     results only when no generation is active. While a run IS active the
     mutator must flag dirty but must NOT wipe the disk out from under the
     running engine.
  3. Re-applying an identical input (same programs / same constraints) is not
     a change and must keep the service clean.

DataStore disk I/O is patched out so these tests never touch real files.
"""

import pytest
from unittest.mock import patch

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


# ---------------------------------------------------------------------------
# 1. Changing the program selection clears stale results + scores DB
# ---------------------------------------------------------------------------

def test_changing_programs_clears_results(monkeypatch):
    """The reported bug: switching programs left old schedules on screen."""
    svc = _make_service(monkeypatch)
    svc._results = ["stale_schedule"]
    svc._results_by_period = {"FALL_Aleph": ["stale"]}
    svc._current_indices = {"FALL_Aleph": 0}
    svc._dirty = False

    svc.select_programs(["83101"])

    assert svc._results == []
    assert svc._results_by_period == {}
    assert svc._current_indices == {}
    assert svc._dirty is True


def test_changing_programs_triggers_clear_results(monkeypatch):
    """select_programs must route through clear_results() on a real change."""
    svc = _make_service(monkeypatch)
    svc._dirty = False
    with patch.object(svc, "clear_results", wraps=svc.clear_results) as spy:
        svc.select_programs(["83101"])
    spy.assert_called_once()


def test_selecting_identical_programs_does_not_clear(monkeypatch):
    """Re-selecting the same programs is not a change - no wipe, stays clean."""
    svc = _make_service(monkeypatch)
    svc.select_programs(["83101"])
    svc._dirty = False
    with patch.object(svc, "clear_results") as spy:
        svc.select_programs(["83101"])   # identical
    spy.assert_not_called()
    assert svc._dirty is False


# ---------------------------------------------------------------------------
# 2. Cleanup is deferred while a generation is active ("explicitly safe")
# ---------------------------------------------------------------------------

def test_constraint_change_during_active_generation_defers_clear(monkeypatch):
    """While generating, a constraint change flags dirty but must NOT wipe."""
    svc = _make_service(monkeypatch)
    svc._results = ["stale_schedule"]
    svc._generation_active = True
    svc._dirty = False

    with patch.object(svc, "clear_results") as spy:
        svc.set_constraint_settings(ConstraintSettings(daily_cap_enabled=True, daily_cap_k=2))

    spy.assert_not_called()             # disk/db left intact for the running engine
    assert svc._results == ["stale_schedule"]
    assert svc._dirty is True           # but the next Generate will re-run


def test_program_change_during_active_generation_defers_clear(monkeypatch):
    svc = _make_service(monkeypatch)
    svc._results = ["stale_schedule"]
    svc._generation_active = True
    svc._dirty = False

    with patch.object(svc, "clear_results") as spy:
        svc.select_programs(["83101"])

    spy.assert_not_called()
    assert svc._results == ["stale_schedule"]
    assert svc._dirty is True


def test_change_after_generation_settles_clears(monkeypatch):
    """Once generation_active is False again, the next change wipes normally."""
    svc = _make_service(monkeypatch)
    svc._results = ["stale_schedule"]
    svc._generation_active = False
    svc._dirty = False

    svc.set_constraint_settings(ConstraintSettings(daily_cap_enabled=True, daily_cap_k=3))

    assert svc._results == []
    assert svc._dirty is True


# ---------------------------------------------------------------------------
# 3. "No relevant change" leaves existing results available
# ---------------------------------------------------------------------------

def test_no_change_keeps_results_and_does_not_need_generation(monkeypatch):
    """When nothing changed and results exist, needs_generation() is False."""
    svc = _make_service(monkeypatch)
    svc.select_programs(["83101"])
    svc._results = ["good_schedule"]
    svc._dirty = False   # pretend a successful run just finished

    assert svc.needs_generation() is False
    # Re-applying the identical selection must not flip that.
    svc.select_programs(["83101"])
    assert svc.needs_generation() is False
    assert svc._results == ["good_schedule"]