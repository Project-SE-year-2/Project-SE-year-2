import pytest
from pathlib import Path

from src.models.schedule_score import ScheduleScore
from src.output.score_repository import ScoreRepository


# ------------------------------------------------------------------
# Fixture — in-memory DB per test
# ------------------------------------------------------------------

@pytest.fixture
def repo(tmp_path):
    """Fresh ScoreRepository backed by a temp file for each test."""
    return ScoreRepository(db_path=tmp_path / "scores.db")


RUN = "run_2026-06-15"


def _score(**kwargs) -> ScheduleScore:
    defaults = dict(avg_gap=7.0, min_gap=3, spread=21, collisions=1, max_per_day=2)
    defaults.update(kwargs)
    return ScheduleScore(**defaults)


# ------------------------------------------------------------------
# save / load
# ------------------------------------------------------------------

def test_save_and_load_single(repo):
    """A saved score is returned by load() with correct values."""
    score = _score(avg_gap=8.5, min_gap=4, spread=15, collisions=0, max_per_day=2)
    repo.save(RUN, 0, score)

    loaded = repo.load(RUN)
    assert len(loaded) == 1
    idx, s = loaded[0]
    assert idx == 0
    assert s.avg_gap == 8.5
    assert s.min_gap == 4
    assert s.spread == 15
    assert s.collisions == 0
    assert s.max_per_day == 2


def test_save_all_and_load(repo):
    """save_all persists multiple scores in one call."""
    scored = [(i, _score(avg_gap=float(i))) for i in range(5)]
    repo.save_all(RUN, scored)

    loaded = repo.load(RUN)
    assert len(loaded) == 5
    for i, (idx, s) in enumerate(loaded):
        assert idx == i
        assert s.avg_gap == float(i)


def test_load_returns_ordered_by_index(repo):
    """load() returns rows ordered by schedule_idx ascending."""
    repo.save(RUN, 2, _score())
    repo.save(RUN, 0, _score())
    repo.save(RUN, 1, _score())

    loaded = repo.load(RUN)
    assert [idx for idx, _ in loaded] == [0, 1, 2]


def test_load_unknown_run_returns_empty(repo):
    """Loading a run that was never saved returns an empty list."""
    assert repo.load("nonexistent_run") == []


# ------------------------------------------------------------------
# replace on duplicate key
# ------------------------------------------------------------------

def test_save_replaces_existing_entry(repo):
    """Saving the same (run_id, schedule_idx) twice replaces the first entry."""
    repo.save(RUN, 0, _score(avg_gap=5.0))
    repo.save(RUN, 0, _score(avg_gap=9.9))

    loaded = repo.load(RUN)
    assert len(loaded) == 1
    assert loaded[0][1].avg_gap == 9.9


# ------------------------------------------------------------------
# list_runs
# ------------------------------------------------------------------

def test_list_runs_returns_all_run_ids(repo):
    """list_runs returns every distinct run_id saved."""
    repo.save("run_A", 0, _score())
    repo.save("run_B", 0, _score())
    repo.save("run_A", 1, _score())

    runs = repo.list_runs()
    assert sorted(runs) == ["run_A", "run_B"]


def test_list_runs_empty_db(repo):
    assert repo.list_runs() == []


# ------------------------------------------------------------------
# delete_run
# ------------------------------------------------------------------

def test_delete_run_removes_entries(repo):
    """delete_run removes all entries for that run_id only."""
    repo.save("run_A", 0, _score())
    repo.save("run_B", 0, _score())

    repo.delete_run("run_A")

    assert repo.load("run_A") == []
    assert len(repo.load("run_B")) == 1


def test_delete_nonexistent_run_is_safe(repo):
    """Deleting a run that does not exist does not raise."""
    repo.delete_run("ghost_run")


# ------------------------------------------------------------------
# clear
# ------------------------------------------------------------------

def test_clear_removes_all_entries(repo):
    """clear() wipes all scores from all runs."""
    repo.save("run_A", 0, _score())
    repo.save("run_B", 0, _score())

    repo.clear()

    assert repo.load("run_A") == []
    assert repo.load("run_B") == []
    assert repo.list_runs() == []
