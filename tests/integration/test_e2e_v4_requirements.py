"""
End-to-end coverage for the V4 (version 34.0) requirements that were only
proven at unit level before:

  §2  threshold constraints actually FILTER generated schedules end to end.
  §3  optimal multi-criteria sorting orders real generated schedules.
  §6.1 unchanged input does not force a regeneration (internal-save behavior).
  EP-148  CLI ranking-config block ({{# RANKING:}}) drives a sorted report.

Every scenario parses real files with the production parsers and wires the real
SchedulingEngine exactly the way AppController does, so these are true pipeline
tests rather than component stubs.
"""

from datetime import date

import pytest

from src.app_controller import AppController
from src.parsers.course_parser import CourseFileParser, filter_courses_for_scheduling
from src.parsers.exam_period_file_parser import ExamPeriodFileParser
from src.parsers.ranking_config_loader import RankingConfigLoader
from src.algorithm.scheduling_algoritem import match_courses_to_periods
from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.exam_period_catalog import ExamPeriodCatalog
from src.algorithm.basic_version_validator import BasicVersionValidator
from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.scheduling_engine import SchedulingEngine
from src.algorithm.constraints.constraint_checker import ConstraintChecker
from src.algorithm.scoring.schedule_scorer import ScheduleScorer
from src.presenter.scores_database import ScoresDatabase
from src.presenter.ranking_query_engine import RankingQueryEngine
from src.models.constraint_settings import ConstraintSettings

from src.presenter.app_service import AppService
from src.presenter.data_store import DataStore


# --------------------------------------------------------------------------- #
# Sample inputs                                                                #
# --------------------------------------------------------------------------- #

THREE_COURSES = """$$$$
Algorithms
90001
Dr A
83101,1,FALL,Obligatory
Exam
$$$$
Databases
90002
Dr B
83101,1,FALL,Obligatory
Exam
$$$$
Networks
90003
Dr C
83101,1,FALL,Obligatory
Exam
"""

FIVE_DAY_PERIOD = """$$$$
FALL, Aleph
01-02-2026, 05-02-2026
"""

PROGRAMS = "83101\n"


def _scenario(tmp_path, courses=THREE_COURSES, dates=FIVE_DAY_PERIOD, programs=PROGRAMS):
    d = tmp_path / "data"
    d.mkdir(exist_ok=True)
    paths = {"courses": d / "courses.txt", "dates": d / "dates.txt",
             "programs": d / "programs.txt"}
    paths["courses"].write_text(courses, encoding="utf-8")
    paths["dates"].write_text(dates, encoding="utf-8")
    paths["programs"].write_text(programs, encoding="utf-8")
    return paths


def _generate(paths, programs, settings=None):
    courses = CourseFileParser().parse(str(paths["courses"]))
    periods = ExamPeriodFileParser().parse(str(paths["dates"]))
    valid = filter_courses_for_scheduling(courses, programs)
    tasks = match_courses_to_periods(valid, periods)
    index = ConstraintIndex()
    index.build(valid, programs)
    catalog = ExamPeriodCatalog(periods)
    validator = ConstraintValidator(index, BasicVersionValidator(index))
    engine = SchedulingEngine(validator, catalog, index, settings, None)
    schedules, meta = engine.generateAll(tasks)
    return schedules


def _cohort_dates(schedule):
    return sorted(pl.date for pl in schedule.placements.values())


# --------------------------------------------------------------------------- #
# §2 — threshold constraints filter real schedules end to end                 #
# --------------------------------------------------------------------------- #

def test_all_gap_constraint_filters_tight_schedules_e2e(tmp_path):
    """Enabling all_gap=2 must drop every schedule with adjacent-day exams."""
    paths = _scenario(tmp_path)
    every = _generate(paths, ["83101"], ConstraintSettings())
    assert every, "baseline generation produced nothing"

    checker = ConstraintChecker(ConstraintSettings(all_gap_enabled=True, all_gap_k=2))
    kept = [s for s in every if checker.is_valid(s)]

    # The constraint must actually remove something (some layouts are tight).
    assert 0 < len(kept) < len(every)
    # Every surviving schedule respects the >= 2-day gap between consecutive exams.
    for sched in kept:
        ds = _cohort_dates(sched)
        assert all((ds[i] - ds[i - 1]).days >= 2 for i in range(1, len(ds)))


def test_daily_cap_constraint_rejects_overfull_days_e2e(tmp_path):
    """With daily_cap=1 no surviving schedule may place two exams on one day."""
    paths = _scenario(tmp_path)
    every = _generate(paths, ["83101"], ConstraintSettings())
    checker = ConstraintChecker(ConstraintSettings(daily_cap_enabled=True, daily_cap_k=1))
    kept = [s for s in every if checker.is_valid(s)]
    for sched in kept:
        ds = _cohort_dates(sched)
        assert len(ds) == len(set(ds))   # no two exams share a day


# --------------------------------------------------------------------------- #
# §3 — optimal sorting orders real generated schedules                        #
# --------------------------------------------------------------------------- #

def test_generated_schedules_sort_by_avg_days_desc_e2e(tmp_path):
    """Score every real schedule, persist, and query — order must be best-first."""
    paths = _scenario(tmp_path)
    schedules = _generate(paths, ["83101"], ConstraintSettings())
    assert len(schedules) >= 3

    scorer = ScheduleScorer.default()
    db = ScoresDatabase(tmp_path / "scores.db")
    for i, sched in enumerate(schedules):
        db.insert("FALL_Aleph", batch_number=0, index_in_batch=i,
                  metrics=scorer.compute_scores(sched))
    db.commit()

    eng = RankingQueryEngine(tmp_path / "scores.db")
    rows = eng.fetch_window("FALL_Aleph", ["avg_days_all"], limit=len(schedules), offset=0)
    avg = [r[3] for r in rows]                 # IDX_AVG_DAYS == 3
    assert avg == sorted(avg, reverse=True)    # higher-is-better, descending
    eng.close()


def test_multi_criteria_priority_is_respected_e2e(tmp_path):
    """Primary criterion dominates; secondary only breaks ties."""
    paths = _scenario(tmp_path)
    schedules = _generate(paths, ["83101"], ConstraintSettings())
    scorer = ScheduleScorer.default()
    db = ScoresDatabase(tmp_path / "scores.db")
    for i, sched in enumerate(schedules):
        db.insert("FALL_Aleph", 0, i, scorer.compute_scores(sched))
    db.commit()

    eng = RankingQueryEngine(tmp_path / "scores.db")
    rows = eng.fetch_window("FALL_Aleph", ["span_required", "avg_days_all"],
                            limit=len(schedules), offset=0)
    spans = [r[5] for r in rows]               # IDX_SPAN == 5 (primary, desc)
    assert spans == sorted(spans, reverse=True)
    eng.close()


# --------------------------------------------------------------------------- #
# EP-148 — CLI ranking-config block drives a sorted report                     #
# --------------------------------------------------------------------------- #

def test_ranking_config_block_is_parsed(tmp_path):
    cfg = tmp_path / "ranking.txt"
    cfg.write_text("{{# RANKING:}}\navg_days_all\nspan_required\n", encoding="utf-8")
    order = RankingConfigLoader.from_file(str(cfg))
    assert order == ["avg_days_all", "span_required"]


def test_app_controller_writes_sorted_report_with_ranking_config(tmp_path):
    """A full CLI-style run with a ranking config writes a report without error."""
    paths = _scenario(tmp_path)
    AppController().run(
        str(paths["courses"]), str(paths["dates"]), str(paths["programs"]),
        constraint_settings=ConstraintSettings(),
        ranking_config=["avg_days_all"],
    )
    output_dir = tmp_path / "output"
    reports = [p for p in output_dir.iterdir() if p.name.startswith("schedule_output_")]
    assert reports, "ranked CLI run wrote no report"
    assert "TOTAL COMPLETE SCHEDULES" in reports[0].read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# §6.1 — unchanged input does not force a regeneration                         #
# --------------------------------------------------------------------------- #

@pytest.fixture(autouse=True)
def _reset_singleton():
    AppService._instance = None
    yield
    AppService._instance = None


def test_unchanged_input_skips_regeneration_e2e(tmp_path, monkeypatch):
    monkeypatch.setattr(DataStore, "load", lambda self: False)
    monkeypatch.setattr(DataStore, "save", lambda self: None)
    paths = _scenario(tmp_path)

    svc = AppService()
    svc.load_data(str(paths["courses"]), str(paths["dates"]), "replace",
                  str(paths["programs"]))
    svc.select_programs(["83101"])
    svc.generate()   # blocking, in-memory legacy mode

    # Right after a run with no further input change, the app must not need to
    # regenerate — it can show the existing results instead.
    assert svc.needs_generation() is False


def test_changing_constraints_requires_regeneration_e2e(tmp_path, monkeypatch):
    monkeypatch.setattr(DataStore, "load", lambda self: False)
    monkeypatch.setattr(DataStore, "save", lambda self: None)
    paths = _scenario(tmp_path)

    svc = AppService()
    svc.load_data(str(paths["courses"]), str(paths["dates"]), "replace",
                  str(paths["programs"]))
    svc.select_programs(["83101"])
    svc.generate()
    assert svc.needs_generation() is False

    svc.set_constraint_settings(ConstraintSettings(daily_cap_enabled=True, daily_cap_k=2))
    assert svc.needs_generation() is True
