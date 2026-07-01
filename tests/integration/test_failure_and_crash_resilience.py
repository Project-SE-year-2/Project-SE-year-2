"""
Failure & crash-resilience tests.

Last sprint we lost points for having a nice CI action but *no tests for failure
and crash scenarios*. This suite deliberately feeds the system bad input, illegal
operations, and impossible problems, and asserts that it fails LOUDLY and
GRACEFULLY — a clear exception or a structured error — never a silent crash or a
corrupt result.

Grouped by the surface that must stay robust:
  - File / input validation
  - Impossible (infeasible) scheduling problems
  - Illegal presenter operations
  - Query-engine / settings guards
  - Manual-edit and config-loader robustness
  - The CLI entry point must never let an exception escape the process
"""

import sys
from datetime import date

import pytest

from src.app_controller import AppController
from src.presenter.app_service import AppService
from src.presenter.data_store import DataStore
from src.presenter.scores_database import ScoresDatabase
from src.presenter.ranking_query_engine import RankingQueryEngine
from src.parsers.ranking_config_loader import RankingConfigLoader
from src.models.constraint_settings import ConstraintSettings


@pytest.fixture(autouse=True)
def _reset_singleton():
    AppService._instance = None
    yield
    AppService._instance = None


def _svc(monkeypatch):
    monkeypatch.setattr(DataStore, "load", lambda self: False)
    monkeypatch.setattr(DataStore, "save", lambda self: None)
    return AppService()


def _write(p, text):
    p.write_text(text, encoding="utf-8")
    return str(p)


# --------------------------------------------------------------------------- #
# File / input validation                                                     #
# --------------------------------------------------------------------------- #

def test_missing_courses_file_raises_file_not_found(tmp_path, monkeypatch):
    svc = _svc(monkeypatch)
    with pytest.raises(FileNotFoundError):
        svc.load_data(str(tmp_path / "nope.txt"), str(tmp_path / "nope2.txt"), "replace")


def test_empty_file_raises_value_error(tmp_path, monkeypatch):
    svc = _svc(monkeypatch)
    empty = _write(tmp_path / "empty.txt", "")
    dates = _write(tmp_path / "d.txt", "$$$$\nFALL, Aleph\n01-01-2026, 01-01-2026\n")
    with pytest.raises(ValueError):
        svc.load_data(empty, dates, "replace")


def test_unknown_load_mode_raises(tmp_path, monkeypatch):
    svc = _svc(monkeypatch)
    c = _write(tmp_path / "c.txt", "$$$$\nX\n90001\nDr\n83101,1,FALL,Obligatory\nExam\n")
    d = _write(tmp_path / "d.txt", "$$$$\nFALL, Aleph\n01-01-2026, 01-01-2026\n")
    with pytest.raises(ValueError):
        svc.load_data(c, d, "sideways")   # not 'replace' or 'append'


def test_app_controller_missing_file_raises(tmp_path):
    with pytest.raises((FileNotFoundError, ValueError)):
        AppController().run(
            str(tmp_path / "a.txt"), str(tmp_path / "b.txt"), str(tmp_path / "c.txt")
        )


# --------------------------------------------------------------------------- #
# Impossible scheduling problems must not crash — they must raise clearly      #
# --------------------------------------------------------------------------- #

def test_infeasible_problem_raises_runtime_error(tmp_path):
    """Four colliding obligatory courses but only two days = no solution."""
    data = tmp_path / "data"
    data.mkdir()
    courses = "".join(
        f"$$$$\nC{i}\n9000{i}\nDr\n83101,1,FALL,Obligatory\nExam\n" for i in range(1, 5)
    )
    _write(data / "courses.txt", courses)
    _write(data / "dates.txt", "$$$$\nFALL, Aleph\n01-02-2026, 02-02-2026\n")
    _write(data / "programs.txt", "83101\n")

    with pytest.raises(RuntimeError):
        AppController().run(
            str(data / "courses.txt"), str(data / "dates.txt"), str(data / "programs.txt")
        )


# --------------------------------------------------------------------------- #
# Illegal presenter operations                                                #
# --------------------------------------------------------------------------- #

def test_generate_without_programs_raises(tmp_path, monkeypatch):
    svc = _svc(monkeypatch)
    with pytest.raises(ValueError):
        svc.generate()   # nothing selected


def test_select_invalid_program_id_raises(monkeypatch):
    svc = _svc(monkeypatch)
    with pytest.raises(ValueError):
        svc.select_programs(["abc"])       # not a 5-digit id
    with pytest.raises(ValueError):
        svc.select_programs(["1", "2", "3", "4", "5", "6"])   # more than 5


def test_navigate_unknown_period_raises(monkeypatch):
    svc = _svc(monkeypatch)
    with pytest.raises(ValueError):
        svc.navigate("NOPE_Aleph", +1)


def test_get_schedule_out_of_range_raises(monkeypatch):
    svc = _svc(monkeypatch)
    with pytest.raises(IndexError):
        svc.get_schedule(999)   # no results loaded


def test_get_schedule_batch_negative_start_raises(monkeypatch):
    svc = _svc(monkeypatch)
    with pytest.raises(IndexError):
        svc.get_schedule_batch(-1, 10)


# --------------------------------------------------------------------------- #
# Query engine / settings guards                                              #
# --------------------------------------------------------------------------- #

def test_ranking_query_rejects_unknown_sort_column(tmp_path):
    ScoresDatabase(tmp_path / "s.db").close()
    eng = RankingQueryEngine(tmp_path / "s.db")
    try:
        with pytest.raises(ValueError):
            eng.fetch_window("p", ["DROP TABLE scores; --"], limit=10, offset=0)
        with pytest.raises(ValueError):
            eng.fetch_window("p", ["avg_days_all"], limit=0, offset=0)   # bad limit
        with pytest.raises(ValueError):
            eng.fetch_window("p", ["avg_days_all"], limit=10, offset=-1)  # bad offset
        with pytest.raises(ValueError):
            eng.best_score("p", "not_a_column")
    finally:
        eng.close()


def test_constraint_settings_reject_nonpositive_k(tmp_path):
    with pytest.raises(ValueError):
        ConstraintSettings(mandatory_gap_enabled=True, mandatory_gap_k=0).validate()
    with pytest.raises(ValueError):
        ConstraintSettings(spread_enabled=True, spread_k=0).validate()


def test_scores_database_clear_unknown_period_is_safe(tmp_path):
    db = ScoresDatabase(tmp_path / "s.db")
    try:
        db.clear_period("never_seen")   # must be a silent no-op, not a crash
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# Manual-edit & config-loader robustness                                      #
# --------------------------------------------------------------------------- #

def test_validate_manual_move_unknown_period_returns_error_not_crash(monkeypatch):
    svc = _svc(monkeypatch)
    monkeypatch.setattr(svc, "get_periods", lambda: [])
    errors = svc.validate_manual_move("GONE_Aleph", [], {"course_number": "1"}, date(2026, 1, 1))
    assert errors and errors[0]["rule"] == "period_not_found"


def test_ranking_config_loader_survives_missing_and_garbage(tmp_path):
    assert RankingConfigLoader.from_file(str(tmp_path / "missing.txt")) == []
    assert RankingConfigLoader.from_file("") == []
    garbage = _write(tmp_path / "g.txt", "hello\n### not a block\nrandom=1\n")
    assert RankingConfigLoader.from_file(garbage) == []   # no valid keys → empty, no crash


# --------------------------------------------------------------------------- #
# The CLI must never let an exception escape the process                      #
# --------------------------------------------------------------------------- #

def test_cli_main_swallows_errors_and_reports(tmp_path, monkeypatch, capsys):
    """cli_main.main must catch failures and print an error, not crash."""
    import src.cli_main as cli_main

    monkeypatch.setattr(sys, "argv", [
        "cli_main",
        "--courses-file", str(tmp_path / "missing_courses.txt"),
        "--dates-file", str(tmp_path / "missing_dates.txt"),
        "--programs-file", str(tmp_path / "missing_programs.txt"),
    ])

    # Must return normally (no propagated exception).
    cli_main.main()

    out = capsys.readouterr().out
    assert "Application Error" in out
