import pytest
from pathlib import Path

from src.models.schedule_score import ScheduleMetrics
from src.output.score_repository import ScoreRepository


@pytest.fixture
def repo(tmp_path):
    return ScoreRepository(db_path=tmp_path / "scores.db")


RUN = "run_2026-06-15"


def _score(**kwargs) -> ScheduleMetrics:
    defaults = dict(avg_days_all=7.0, min_days_required=3, span_required=21,
                    elective_conflicts=1, max_exams_per_day=2)
    defaults.update(kwargs)
    return ScheduleMetrics(**defaults)


def test_save_and_load_single(repo):
    score = _score(avg_days_all=8.5, min_days_required=4, span_required=15,
                   elective_conflicts=0, max_exams_per_day=2)
    repo.save(RUN, 0, score)
    loaded = repo.load(RUN)
    assert len(loaded) == 1
    idx, s = loaded[0]
    assert idx == 0
    assert s.avg_days_all == 8.5
    assert s.min_days_required == 4
    assert s.span_required == 15
    assert s.elective_conflicts == 0
    assert s.max_exams_per_day == 2


def test_save_all_and_load(repo):
    scored = [(i, _score(avg_days_all=float(i))) for i in range(5)]
    repo.save_all(RUN, scored)
    loaded = repo.load(RUN)
    assert len(loaded) == 5
    for i, (idx, s) in enumerate(loaded):
        assert idx == i
        assert s.avg_days_all == float(i)


def test_load_returns_ordered_by_index(repo):
    repo.save(RUN, 2, _score())
    repo.save(RUN, 0, _score())
    repo.save(RUN, 1, _score())
    assert [idx for idx, _ in repo.load(RUN)] == [0, 1, 2]


def test_load_unknown_run_returns_empty(repo):
    assert repo.load("nonexistent_run") == []


def test_save_replaces_existing_entry(repo):
    repo.save(RUN, 0, _score(avg_days_all=5.0))
    repo.save(RUN, 0, _score(avg_days_all=9.9))
    loaded = repo.load(RUN)
    assert len(loaded) == 1
    assert loaded[0][1].avg_days_all == 9.9


def test_list_runs_returns_all_run_ids(repo):
    repo.save("run_A", 0, _score())
    repo.save("run_B", 0, _score())
    repo.save("run_A", 1, _score())
    assert sorted(repo.list_runs()) == ["run_A", "run_B"]


def test_list_runs_empty_db(repo):
    assert repo.list_runs() == []


def test_delete_run_removes_entries(repo):
    repo.save("run_A", 0, _score())
    repo.save("run_B", 0, _score())
    repo.delete_run("run_A")
    assert repo.load("run_A") == []
    assert len(repo.load("run_B")) == 1


def test_delete_nonexistent_run_is_safe(repo):
    repo.delete_run("ghost_run")


def test_clear_removes_all_entries(repo):
    repo.save("run_A", 0, _score())
    repo.save("run_B", 0, _score())
    repo.clear()
    assert repo.load("run_A") == []
    assert repo.list_runs() == []
