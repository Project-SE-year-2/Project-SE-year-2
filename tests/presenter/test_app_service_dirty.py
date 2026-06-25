"""
EP-149 — tests for the "needs regeneration" flag and stale-result clearing.

Two related bugs are covered here:

  Bug 3 — Generate must NOT re-run the engine when nothing changed since the
          last run. AppService tracks this with a dirty flag exposed through
          needs_generation().

  Bug 2 — Changing inputs (new files, edited constraints, edited periods) must
          wipe the previous run so the output screen can't show stale results.
          AppService.clear_results() does the wipe and is triggered by those
          input changes.

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
# needs_generation() — the dirty flag (Bug 3)
# ---------------------------------------------------------------------------

def test_fresh_service_needs_generation(monkeypatch):
    """A brand-new service has no results, so it must regenerate."""
    svc = _make_service(monkeypatch)
    assert svc.needs_generation() is True


def test_clean_after_generation(monkeypatch):
    """A successful blocking generate() clears the dirty flag."""
    svc = _make_service(monkeypatch)
    svc._selected_programs = ["83101"]
    # Stub the engine so generate() returns without real scheduling.
    with patch.object(svc, "_prepare_engine") as prep:
        engine = prep.return_value[0]
        engine.generateAll.return_value = (["sched_a", "sched_b"], {})
        prep.return_value = (engine, {})
        svc.generate()
    assert svc.needs_generation() is False


def test_changing_constraints_marks_dirty(monkeypatch):
    """Editing the constraints must require a fresh run."""
    svc = _make_service(monkeypatch)
    svc._dirty = False   # pretend a run just completed
    svc.set_constraint_settings(ConstraintSettings(all_gap_enabled=True, all_gap_k=5))
    assert svc.needs_generation() is True


def test_setting_identical_constraints_does_not_mark_dirty(monkeypatch):
    """Re-applying the exact same constraints is not a change."""
    svc = _make_service(monkeypatch)
    same = svc.get_constraint_settings()
    svc._dirty = False
    svc.set_constraint_settings(same)
    # No results exist, so needs_generation() is still True — but only because
    # the count is zero, not because we were flagged dirty.
    assert svc._dirty is False


def test_selecting_different_programs_marks_dirty(monkeypatch):
    svc = _make_service(monkeypatch)
    svc._dirty = False
    svc.select_programs(["83101"])
    assert svc._dirty is True


def test_selecting_same_programs_keeps_clean(monkeypatch):
    svc = _make_service(monkeypatch)
    svc.select_programs(["83101"])
    svc._dirty = False
    svc.select_programs(["83101"])   # identical selection
    assert svc._dirty is False


# ---------------------------------------------------------------------------
# clear_results() — stale-result wiping (Bug 2)
# ---------------------------------------------------------------------------

def test_clear_results_empties_in_memory_state(monkeypatch):
    svc = _make_service(monkeypatch)
    svc._results = ["x"]
    svc._results_by_period = {"FALL_Aleph": ["x"]}
    svc._current_indices = {"FALL_Aleph": 0}
    svc._sorted_cache = {"FALL_Aleph": [(0, 0)]}

    svc.clear_results()

    assert svc._results == []
    assert svc._results_by_period == {}
    assert svc._current_indices == {}
    assert svc._sorted_cache == {}


def test_changing_constraints_clears_results(monkeypatch):
    """The reported bug: old schedules must not survive a constraint change."""
    svc = _make_service(monkeypatch)
    svc._results = ["stale_schedule"]
    svc.set_constraint_settings(ConstraintSettings(daily_cap_enabled=True, daily_cap_k=2))
    assert svc._results == []


def test_clear_results_is_safe_to_call_twice(monkeypatch):
    svc = _make_service(monkeypatch)
    svc.clear_results()
    svc.clear_results()   # must not raise
    assert svc._results == []
