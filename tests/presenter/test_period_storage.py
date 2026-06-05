"""
Tests for File Storage & Per-Period Navigation (EP-82).

Covers:
— PeriodResultsWriter: batches of 50, manifest updated after each
— ResultsReader: loads only the relevant batch file
— AppService.navigate() is per-period independent; export_current()
  combines current indices into one file
— generate_stream() in file-based mode never calls ScheduleCombiner
  and leaves _results empty
"""

import json
from datetime import date
from unittest.mock import MagicMock

import pytest

from src.algorithm.generation_result import PeriodGenerationResult
from src.algorithm.period_results_writer import PeriodResultsWriter
from src.models.course import Course
from src.models.enums import Evaluation, Moed, ReqType, Semester
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.models.program_requirement import ProgramRequirement
from src.presenter.app_service import AppService
from src.presenter.results_reader import ResultsReader


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _make_course(course_id: str, program_id: str) -> Course:
    course = Course(f"Course {course_id}", course_id, "Prof. Test", Evaluation.Exam)
    course.add_requirement(
        ProgramRequirement(program_id, 1, Semester.FALL, ReqType.Obligatory)
    )
    return course


def _make_period(
    semester: Semester = Semester.FALL,
    moed: Moed = Moed.Aleph,
    start: str = "01-01-2026",
    end: str = "02-01-2026",
) -> ExamPeriod:
    period = ExamPeriod(semester, moed, start, end)
    period.possible_dates = [date(2026, 1, 1), date(2026, 1, 2)]
    return period


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture(autouse=True)
def reset_singleton():
    AppService._instance = None
    yield
    AppService._instance = None


# ================================================================== #
# PeriodResultsWriter                                                #
# ================================================================== #

def test_writer_splits_into_batches_of_50(tmp_path):
    writer = PeriodResultsWriter(root_path=tmp_path / "results")
    period = _make_period()
    schedules = [
        ExamSchedule(period) for _ in range(70)
    ]
    for i, s in enumerate(schedules):
        s.assign(_make_course(f"C{i}", "83101"), date(2026, 1, 1))

    writer.write_batch("FALL_Aleph", schedules)

    root = tmp_path / "results"
    assert (root / "FALL_Aleph" / "batch_0000.pkl").exists()
    assert (root / "FALL_Aleph" / "batch_0001.pkl").exists()
    assert not (root / "FALL_Aleph" / "batch_0002.pkl").exists()


def test_writer_never_overwrites_existing_batch(tmp_path):
    writer = PeriodResultsWriter(root_path=tmp_path / "results")
    period = _make_period()

    first = [ExamSchedule(period) for _ in range(50)]
    for i, s in enumerate(first):
        s.assign(_make_course(f"C{i}", "83101"), date(2026, 1, 1))
    writer.write_batch("FALL_Aleph", first)

    second = [ExamSchedule(period) for _ in range(50)]
    for i, s in enumerate(second):
        s.assign(_make_course(f"D{i}", "83101"), date(2026, 1, 2))
    writer.write_batch("FALL_Aleph", second)

    manifest = json.loads(
        (tmp_path / "results" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["FALL_Aleph"] == 100
    assert (tmp_path / "results" / "FALL_Aleph" / "batch_0001.pkl").exists()


def test_writer_updates_manifest_after_every_batch(tmp_path):
    writer = PeriodResultsWriter(root_path=tmp_path / "results")
    period = _make_period()
    schedules = [ExamSchedule(period) for _ in range(70)]
    for i, s in enumerate(schedules):
        s.assign(_make_course(f"C{i}", "83101"), date(2026, 1, 1))

    writer.write_batch("FALL_Aleph", schedules)

    manifest = json.loads(
        (tmp_path / "results" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["FALL_Aleph"] == 70


# ================================================================== #
# ResultsReader                                                      #
# ================================================================== #

def test_reader_loads_only_relevant_batch(tmp_path):
    root = tmp_path / "results"
    writer = PeriodResultsWriter(root_path=root)
    reader = ResultsReader(root_path=root)
    period = _make_period()

    schedules = []
    for i in range(60):
        s = ExamSchedule(period)
        s.assign(_make_course(f"C{i}", "83101"), date(2026, 1, 1 if i < 50 else 2))
        schedules.append(s)
    writer.write_batch("FALL_Aleph", schedules)

    assert reader.get_count("FALL_Aleph") == 60

    def _id_date_map(schedule):
        return {c.course_id: d for c, d in schedule.assignments.items()}

    # Pickle round-trip creates new Course instances — compare by course_id, not object identity
    assert _id_date_map(reader.get_schedule_at("FALL_Aleph", 0)) == _id_date_map(schedules[0])
    assert _id_date_map(reader.get_schedule_at("FALL_Aleph", 50)) == _id_date_map(schedules[50])


def test_reader_get_count_reads_manifest_only(tmp_path):
    root = tmp_path / "results"
    writer = PeriodResultsWriter(root_path=root)
    reader = ResultsReader(root_path=root)
    period = _make_period()

    schedules = [ExamSchedule(period) for _ in range(3)]
    for i, s in enumerate(schedules):
        s.assign(_make_course(f"C{i}", "83101"), date(2026, 1, 1))
    writer.write_batch("FALL_Aleph", schedules)

    # get_count must not load any .pkl - only manifest
    assert reader.get_count("FALL_Aleph") == 3
    assert reader.get_count("NONEXISTENT") == 0


# ================================================================== #
# AppService.navigate() and export_current()                         #
# ================================================================== #

def test_navigate_moves_only_the_requested_period(tmp_path):
    root = tmp_path / "results"
    writer = PeriodResultsWriter(root_path=root)
    reader = ResultsReader(root_path=root)

    app = AppService()
    app._results_writer = writer
    app._results_reader = reader
    app._selected_programs = ["83101"]

    fall = _make_period()
    bet_period = ExamPeriod(Semester.FALL, Moed.Bet, "03-01-2026", "04-01-2026")
    bet_period.possible_dates = [date(2026, 1, 3), date(2026, 1, 4)]

    fall_scheds = []
    for i in range(2):
        s = ExamSchedule(fall)
        s.assign(_make_course(f"F{i}", "83101"), date(2026, 1, 1))
        fall_scheds.append(s)
    bet_sched = ExamSchedule(bet_period)
    bet_sched.assign(_make_course("B1", "83101"), date(2026, 1, 3))

    writer.write_batch("FALL_Aleph", fall_scheds)
    writer.write_batch("FALL_Bet", [bet_sched])
    app._current_indices = {"FALL_Aleph": 0, "FALL_Bet": 0}

    result = app.navigate("FALL_Aleph", 1)

    assert result["period_id"] == "FALL_Aleph"
    assert result["index"] == 1
    assert app._current_indices["FALL_Aleph"] == 1
    assert app._current_indices["FALL_Bet"] == 0   # untouched


def test_get_schedule_count_per_period_reads_manifest(tmp_path):
    root = tmp_path / "results"
    writer = PeriodResultsWriter(root_path=root)
    reader = ResultsReader(root_path=root)

    app = AppService()
    app._results_reader = reader
    fall = _make_period()

    scheds = []
    for i in range(2):
        s = ExamSchedule(fall)
        s.assign(_make_course(f"F{i}", "83101"), date(2026, 1, 1))
        scheds.append(s)
    writer.write_batch("FALL_Aleph", scheds)
    writer.write_batch("FALL_Bet", [scheds[0]])

    assert app.get_schedule_count("FALL_Aleph") == 2
    assert app.get_schedule_count("FALL_Bet") == 1


def test_export_current_combines_one_schedule_per_period(tmp_path):
    root = tmp_path / "results"
    writer = PeriodResultsWriter(root_path=root)
    reader = ResultsReader(root_path=root)

    app = AppService()
    app._results_writer = writer
    app._results_reader = reader
    app._selected_programs = ["83101"]

    fall = _make_period()
    bet_period = ExamPeriod(Semester.FALL, Moed.Bet, "03-01-2026", "04-01-2026")
    bet_period.possible_dates = [date(2026, 1, 3), date(2026, 1, 4)]

    fall_scheds = []
    for i in range(2):
        s = ExamSchedule(fall)
        s.assign(_make_course(f"F{i}", "83101"), date(2026, 1, 1))
        fall_scheds.append(s)
    bet_sched = ExamSchedule(bet_period)
    bet_sched.assign(_make_course("B1", "83101"), date(2026, 1, 3))

    writer.write_batch("FALL_Aleph", fall_scheds)
    writer.write_batch("FALL_Bet", [bet_sched])

    # Navigate FALL_Aleph forward - now showing index 1 ("Course F1")
    app._current_indices = {"FALL_Aleph": 0, "FALL_Bet": 0}
    app.navigate("FALL_Aleph", 1)

    export_path = tmp_path / "export.txt"
    app.export_current(str(export_path))

    assert export_path.exists()
    contents = export_path.read_text(encoding="utf-8")
    assert "Course F1" in contents
    assert "Course B1" in contents


# ================================================================== #
# navigate() — per-period bounds                                      #
# ================================================================== #

def test_navigate_raises_index_error_at_upper_bound(tmp_path):
    root = tmp_path / "results"
    writer = PeriodResultsWriter(root_path=root)
    reader = ResultsReader(root_path=root)
    app = AppService()
    app._results_reader = reader
    fall = _make_period()

    s = ExamSchedule(fall)
    s.assign(_make_course("C1", "83101"), date(2026, 1, 1))
    writer.write_batch("FALL_Aleph", [s])
    app._current_indices = {"FALL_Aleph": 0}

    with pytest.raises(IndexError):
        app.navigate("FALL_Aleph", +1)   # only 1 schedule — index 1 is out of range


def test_navigate_raises_index_error_at_lower_bound(tmp_path):
    root = tmp_path / "results"
    writer = PeriodResultsWriter(root_path=root)
    reader = ResultsReader(root_path=root)
    app = AppService()
    app._results_reader = reader
    fall = _make_period()

    s = ExamSchedule(fall)
    s.assign(_make_course("C1", "83101"), date(2026, 1, 1))
    writer.write_batch("FALL_Aleph", [s])
    app._current_indices = {"FALL_Aleph": 0}

    with pytest.raises(IndexError):
        app.navigate("FALL_Aleph", -1)   # already at 0 — can't go back


def test_navigate_raises_value_error_for_unknown_period(tmp_path):
    app = AppService()
    app._results_reader = ResultsReader(root_path=tmp_path / "results")
    app._current_indices = {}

    with pytest.raises(ValueError, match="FALL_Aleph"):
        app.navigate("FALL_Aleph", 1)


# ================================================================== #
# navigate_global() — odometer carry across all periods              #
# ================================================================== #

def _setup_two_period_app(tmp_path):
    """Helper: 2 periods × 2 solutions each. Returns (app, reader)."""
    root = tmp_path / "results"
    writer = PeriodResultsWriter(root_path=root)
    reader = ResultsReader(root_path=root)

    app = AppService()
    app._results_reader = reader
    app._selected_programs = ["83101"]

    fall = _make_period()
    bet_period = ExamPeriod(Semester.FALL, Moed.Bet, "03-01-2026", "04-01-2026")
    bet_period.possible_dates = [date(2026, 1, 3), date(2026, 1, 4)]

    for i in range(2):
        s = ExamSchedule(fall)
        s.assign(_make_course(f"F{i}", "83101"), date(2026, 1, 1))
        writer.write_batch("FALL_Aleph", [s])

    for i in range(2):
        s = ExamSchedule(bet_period)
        s.assign(_make_course(f"B{i}", "83101"), date(2026, 1, 3))
        writer.write_batch("FALL_Bet", [s])

    app._current_indices = {"FALL_Aleph": 0, "FALL_Bet": 0}
    return app


def test_navigate_global_forward_visits_all_combinations(tmp_path):
    """navigate_global(+1) iterates all 4 combinations in odometer order."""
    app = _setup_two_period_app(tmp_path)

    visited = [dict(app._current_indices)]
    while True:
        try:
            app.navigate_global(+1)
            visited.append(dict(app._current_indices))
        except IndexError:
            break

    assert visited == [
        {"FALL_Aleph": 0, "FALL_Bet": 0},
        {"FALL_Aleph": 0, "FALL_Bet": 1},
        {"FALL_Aleph": 1, "FALL_Bet": 0},
        {"FALL_Aleph": 1, "FALL_Bet": 1},
    ]


def test_navigate_global_backward_from_last(tmp_path):
    """navigate_global(-1) from the last combination steps back correctly."""
    app = _setup_two_period_app(tmp_path)
    app._current_indices = {"FALL_Aleph": 1, "FALL_Bet": 1}

    app.navigate_global(-1)
    assert app._current_indices == {"FALL_Aleph": 1, "FALL_Bet": 0}

    app.navigate_global(-1)
    assert app._current_indices == {"FALL_Aleph": 0, "FALL_Bet": 1}


def test_navigate_global_raises_at_last_combination(tmp_path):
    """navigate_global(+1) raises IndexError at the very last combination."""
    app = _setup_two_period_app(tmp_path)
    app._current_indices = {"FALL_Aleph": 1, "FALL_Bet": 1}

    with pytest.raises(IndexError, match="last"):
        app.navigate_global(+1)

    # State must be unchanged after the failed navigation
    assert app._current_indices == {"FALL_Aleph": 1, "FALL_Bet": 1}


def test_navigate_global_raises_at_first_combination(tmp_path):
    """navigate_global(-1) raises IndexError at the very first combination."""
    app = _setup_two_period_app(tmp_path)
    app._current_indices = {"FALL_Aleph": 0, "FALL_Bet": 0}

    with pytest.raises(IndexError, match="first"):
        app.navigate_global(-1)

    # State must be unchanged after the failed navigation
    assert app._current_indices == {"FALL_Aleph": 0, "FALL_Bet": 0}


# ================================================================== #
# No ScheduleCombiner in file-based flow                             #
# ================================================================== #

def test_generate_stream_file_mode_skips_combiner(tmp_path, monkeypatch):
    """In file-based mode _results stays empty (combiner never ran) and
    _current_indices is populated for every period that was solved."""
    root = tmp_path / "results"
    writer = PeriodResultsWriter(root_path=root)
    reader = ResultsReader(root_path=root)

    app = AppService()
    app._results_writer = writer
    app._results_reader = reader
    app._selected_programs = ["83101"]

    fall = _make_period()
    course = _make_course("C1", "83101")
    sched = ExamSchedule(fall)
    sched.assign(course, date(2026, 1, 1))

    # solve_to_disk is called per period — simulate it writing one schedule
    def fake_solve_to_disk(period, courses_dict, w):
        pid = f"{period.semester.value}_{period.moed.value}"
        w.write_batch(pid, [sched])

    mock_engine = MagicMock()
    mock_engine.solve_to_disk.side_effect = fake_solve_to_disk
    # scheduling_tasks must contain the period so the loop body runs
    monkeypatch.setattr(app, "_prepare_engine", lambda: (mock_engine, {fall: {}}))

    list(app.generate_stream())

    # ScheduleCombiner was NOT used - _results stays empty
    assert app._results == []
    # Per-period navigation is ready
    assert app._current_indices == {"FALL_Aleph": 0}
    # Batch was actually written to disk
    assert reader.get_count("FALL_Aleph") == 1
