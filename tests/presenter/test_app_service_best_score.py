"""
EP-150 — tests for AppService.get_best_score().

get_best_score() exposes the rank-1 value of the active primary sort column so
the output screen can detect when a strictly better schedule has been found and
raise a notification. These tests patch the ranking engine so no real scores.db
is needed.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.presenter.app_service import AppService
from src.presenter.data_store import DataStore


@pytest.fixture(autouse=True)
def reset_singleton():
    AppService._instance = None
    yield
    AppService._instance = None


def _make_service(monkeypatch) -> AppService:
    monkeypatch.setattr(DataStore, "load", lambda self: False)
    monkeypatch.setattr(DataStore, "save", lambda self: None)
    return AppService()


def test_returns_none_when_no_sort_active(monkeypatch):
    svc = _make_service(monkeypatch)
    svc.set_sort_order([])           # no sort
    assert svc.get_best_score("FALL_Aleph") is None


def test_returns_none_when_no_ranking_engine(monkeypatch):
    svc = _make_service(monkeypatch)
    svc.set_sort_order(["avg_days_all"])
    with patch.object(svc, "_get_ranking_engine", return_value=None):
        assert svc.get_best_score("FALL_Aleph") is None


def test_queries_primary_sort_column(monkeypatch):
    svc = _make_service(monkeypatch)
    svc.set_sort_order(["avg_days_all", "span_required"])

    engine = MagicMock()
    engine.best_score.return_value = 8.0
    with patch.object(svc, "_get_ranking_engine", return_value=engine):
        result = svc.get_best_score("FALL_Aleph")

    assert result == 8.0
    # Only the primary (first) column drives the "best" value.
    engine.best_score.assert_called_once_with("FALL_Aleph", "avg_days_all")


def test_swallows_engine_errors_as_none(monkeypatch):
    svc = _make_service(monkeypatch)
    svc.set_sort_order(["avg_days_all"])

    engine = MagicMock()
    engine.best_score.side_effect = RuntimeError("db gone")
    with patch.object(svc, "_get_ranking_engine", return_value=engine):
        assert svc.get_best_score("FALL_Aleph") is None
