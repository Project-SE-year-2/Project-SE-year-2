"""
Tests for the Presenter-layer streaming pipeline.

Covers:
  - AppService.generate_stream()  — yield behavior, cache population, combiner
  - AppService.get_period_ids()   — arrival order
  - AppService.get_period_schedules() — format, KeyError, program filtering

The SchedulingEngine is fully mocked. These tests verify Presenter
behaviour only — algorithm correctness is covered in tests/algorithm/.
"""

import pytest
from datetime import date
from unittest.mock import MagicMock

from src.presenter.app_service import AppService
from src.algorithm.generation_result import PeriodGenerationResult
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.models.course import Course
from src.models.program_requirement import ProgramRequirement
from src.models.enums import Semester, Moed, Evaluation, ReqType


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _make_period(semester: Semester, moed: Moed, start: date, end: date) -> ExamPeriod:
    p = ExamPeriod(semester, moed, start, end)
    p.possible_dates = [start, end]
    return p


def _make_course(cid: str, name: str, program_id: str) -> Course:
    c = Course(name, cid, "Prof. Test", Evaluation.Exam)
    c.add_requirement(ProgramRequirement(program_id, 1, Semester.FALL, ReqType.Obligatory))
    return c


def _make_schedule(period: ExamPeriod, course: Course, exam_date: date) -> ExamSchedule:
    s = ExamSchedule(period)
    s.assign(course, exam_date)
    return s


def _make_result(period: ExamPeriod, schedules: list) -> PeriodGenerationResult:
    return PeriodGenerationResult(
        period=period,
        schedules=schedules,
        metadata={
            "valid_count": len(schedules),
            "theoretical_count": len(schedules),
            "courses": [],
            "available_days": 2,
        },
    )


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture(autouse=True)
def reset_singleton():
    """Isolate each test from the Singleton state."""
    AppService._instance = None
    yield
    AppService._instance = None


@pytest.fixture
def service() -> AppService:
    svc = AppService()
    svc._selected_programs = ["83101"]
    return svc


# ================================================================== #
# generate_stream — yield behaviour                                   #
# ================================================================== #

def test_generate_stream_yields_one_tuple_per_period(service, monkeypatch):
    fall = _make_period(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 2))
    spri = _make_period(Semester.SPRI, Moed.Aleph, date(2026, 7, 1), date(2026, 7, 2))
    course_f = _make_course("83102", "Physics", "83101")
    course_s = _make_course("83112", "Calculus", "83101")
    sched_f = _make_schedule(fall, course_f, date(2026, 2, 1))
    sched_s = _make_schedule(spri, course_s, date(2026, 7, 1))

    mock_engine = MagicMock()
    mock_engine.iterPeriodResults.return_value = iter([
        _make_result(fall, [sched_f]),
        _make_result(spri, [sched_s]),
    ])
    monkeypatch.setattr(service, "_prepare_engine", lambda: (mock_engine, {}))

    yielded = list(service.generate_stream())

    assert len(yielded) == 2
    assert yielded[0][0] == "FALL_Aleph"
    assert yielded[1][0] == "SPRI_Aleph"
    assert yielded[0][1] == [sched_f]
    assert yielded[1][1] == [sched_s]


def test_generate_stream_handles_period_with_zero_schedules(service, monkeypatch):
    """A period that yields no valid schedules must still be cached and yielded."""
    fall = _make_period(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 2))

    mock_engine = MagicMock()
    mock_engine.iterPeriodResults.return_value = iter([_make_result(fall, [])])
    monkeypatch.setattr(service, "_prepare_engine", lambda: (mock_engine, {}))

    yielded = list(service.generate_stream())

    assert len(yielded) == 1
    assert yielded[0][0] == "FALL_Aleph"
    assert yielded[0][1] == []


def test_generate_stream_handles_empty_task_set(service, monkeypatch):
    mock_engine = MagicMock()
    mock_engine.iterPeriodResults.return_value = iter([])
    monkeypatch.setattr(service, "_prepare_engine", lambda: (mock_engine, {}))

    yielded = list(service.generate_stream())

    assert yielded == []


def test_generate_stream_raises_if_no_programs_selected():
    svc = AppService()
    # _selected_programs is empty by default
    with pytest.raises(ValueError, match="No programs selected"):
        list(svc.generate_stream())


# ================================================================== #
# generate_stream — cache population                                  #
# ================================================================== #

def test_generate_stream_populates_cache_incrementally(service, monkeypatch):
    """_results_by_period must be empty before the first yield and filled after."""
    fall = _make_period(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 2))
    course = _make_course("83102", "Physics", "83101")
    sched = _make_schedule(fall, course, date(2026, 2, 1))

    mock_engine = MagicMock()
    mock_engine.iterPeriodResults.return_value = iter([_make_result(fall, [sched])])
    monkeypatch.setattr(service, "_prepare_engine", lambda: (mock_engine, {}))

    gen = service.generate_stream()
    assert service._results_by_period == {}   # nothing yet

    next(gen)
    assert service._results_by_period["FALL_Aleph"] == [sched]


def test_generate_stream_resets_cache_on_second_call(service, monkeypatch):
    """Calling generate_stream() twice must not accumulate stale entries."""
    fall = _make_period(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 2))
    course = _make_course("83102", "Physics", "83101")
    sched = _make_schedule(fall, course, date(2026, 2, 1))

    mock_engine = MagicMock()
    mock_engine.iterPeriodResults.return_value = iter([_make_result(fall, [sched])])
    monkeypatch.setattr(service, "_prepare_engine", lambda: (mock_engine, {}))

    service._results_by_period = {"STALE_KEY": []}  # leftover from a previous run

    list(service.generate_stream())

    assert "STALE_KEY" not in service._results_by_period
    assert "FALL_Aleph" in service._results_by_period


# ================================================================== #
# generate_stream — ScheduleCombiner runs at the end                 #
# ================================================================== #

def test_generate_stream_runs_combiner_after_all_periods(service, monkeypatch):
    """_results must be populated with cross-period schedules once the stream ends."""
    fall = _make_period(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 2))
    spri = _make_period(Semester.SPRI, Moed.Aleph, date(2026, 7, 1), date(2026, 7, 2))
    course_f = _make_course("83102", "Physics", "83101")
    course_s = _make_course("83112", "Calculus", "83101")
    sched_f = _make_schedule(fall, course_f, date(2026, 2, 1))
    sched_s = _make_schedule(spri, course_s, date(2026, 7, 1))

    mock_engine = MagicMock()
    mock_engine.iterPeriodResults.return_value = iter([
        _make_result(fall, [sched_f]),
        _make_result(spri, [sched_s]),
    ])
    monkeypatch.setattr(service, "_prepare_engine", lambda: (mock_engine, {}))

    assert service._results == []

    list(service.generate_stream())

    # 1 fall schedule × 1 spring schedule = 1 combined cross-period schedule
    assert len(service._results) == 1
    assert service._results[0].is_cross_period


def test_get_schedule_count_returns_cartesian_product_size(service, monkeypatch):
    """2 fall × 3 spring = 6 combined schedules."""
    fall = _make_period(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 3))
    spri = _make_period(Semester.SPRI, Moed.Aleph, date(2026, 7, 1), date(2026, 7, 4))
    course_f = _make_course("83102", "Physics", "83101")
    course_s = _make_course("83112", "Calculus", "83101")

    scheds_f = [_make_schedule(fall, course_f, date(2026, 2, d)) for d in (1, 2)]
    scheds_s = [_make_schedule(spri, course_s, date(2026, 7, d)) for d in (1, 2, 3)]

    mock_engine = MagicMock()
    mock_engine.iterPeriodResults.return_value = iter([
        _make_result(fall, scheds_f),
        _make_result(spri, scheds_s),
    ])
    monkeypatch.setattr(service, "_prepare_engine", lambda: (mock_engine, {}))

    list(service.generate_stream())

    assert service.get_schedule_count() == 6


def test_get_schedule_count_is_zero_when_all_periods_empty(service, monkeypatch):
    fall = _make_period(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 2))
    spri = _make_period(Semester.SPRI, Moed.Aleph, date(2026, 7, 1), date(2026, 7, 2))

    mock_engine = MagicMock()
    mock_engine.iterPeriodResults.return_value = iter([
        _make_result(fall, []),
        _make_result(spri, []),
    ])
    monkeypatch.setattr(service, "_prepare_engine", lambda: (mock_engine, {}))

    list(service.generate_stream())

    assert service.get_schedule_count() == 0


# ================================================================== #
# get_period_ids                                                       #
# ================================================================== #

def test_get_period_ids_empty_before_any_generation(service):
    assert service.get_period_ids() == []


def test_get_period_ids_reflects_completion_arrival_order(service, monkeypatch):
    """Periods may complete out of calendar order; ids must reflect arrival, not calendar order."""
    fall = _make_period(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 2))
    spri = _make_period(Semester.SPRI, Moed.Aleph, date(2026, 7, 1), date(2026, 7, 2))
    summ = _make_period(Semester.SUMM, Moed.Aleph, date(2026, 9, 1), date(2026, 9, 2))

    mock_engine = MagicMock()
    # Spring finishes first, then Summer, then Fall
    mock_engine.iterPeriodResults.return_value = iter([
        _make_result(spri, []),
        _make_result(summ, []),
        _make_result(fall, []),
    ])
    monkeypatch.setattr(service, "_prepare_engine", lambda: (mock_engine, {}))

    list(service.generate_stream())

    assert service.get_period_ids() == ["SPRI_Aleph", "SUMM_Aleph", "FALL_Aleph"]


# ================================================================== #
# get_period_schedules                                                 #
# ================================================================== #

def test_get_period_schedules_raises_key_error_for_unknown_period(service):
    with pytest.raises(KeyError, match="FALL_Aleph"):
        service.get_period_schedules("FALL_Aleph")


def test_get_period_schedules_returns_empty_list_for_zero_schedule_period(service, monkeypatch):
    fall = _make_period(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 2))

    mock_engine = MagicMock()
    mock_engine.iterPeriodResults.return_value = iter([_make_result(fall, [])])
    monkeypatch.setattr(service, "_prepare_engine", lambda: (mock_engine, {}))

    list(service.generate_stream())

    assert service.get_period_schedules("FALL_Aleph") == []


def test_get_period_schedules_returns_all_required_fields(service, monkeypatch):
    fall = _make_period(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 2))
    course = _make_course("83102", "Physics 1", "83101")
    sched = _make_schedule(fall, course, date(2026, 2, 1))

    mock_engine = MagicMock()
    mock_engine.iterPeriodResults.return_value = iter([_make_result(fall, [sched])])
    monkeypatch.setattr(service, "_prepare_engine", lambda: (mock_engine, {}))

    list(service.generate_stream())

    result = service.get_period_schedules("FALL_Aleph")

    assert len(result) == 1
    entry = result[0]
    assert entry["course_number"] == "83102"
    assert entry["course_name"]   == "Physics 1"
    assert entry["exam_date"]     == date(2026, 2, 1)
    assert entry["semester"]      == "FALL"
    assert entry["moed"]          == "Aleph"
    assert entry["programs"]      == ["83101"]
    assert entry["type"]          == "Obligatory"


def test_get_period_schedules_uses_enum_value_not_name(service, monkeypatch):
    """semester and moed must be .value strings, not enum names."""
    spri = _make_period(Semester.SPRI, Moed.Bet, date(2026, 8, 1), date(2026, 8, 2))
    course = _make_course("83102", "Physics", "83101")
    sched = _make_schedule(spri, course, date(2026, 8, 1))

    mock_engine = MagicMock()
    mock_engine.iterPeriodResults.return_value = iter([_make_result(spri, [sched])])
    monkeypatch.setattr(service, "_prepare_engine", lambda: (mock_engine, {}))

    list(service.generate_stream())

    result = service.get_period_schedules("SPRI_Bet")
    assert result[0]["semester"] == "SPRI"    # .value, not "SPRI" enum name (same here, but Moed differs)
    assert result[0]["moed"]     == "Bet"     # .value == "Bet", not "BET"


def test_get_period_schedules_filters_to_selected_programs_only(service, monkeypatch):
    """Course belongs to two programs; only the selected one appears in programs list."""
    fall = _make_period(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 2))

    course = Course("Physics", "83102", "Prof. A", Evaluation.Exam)
    course.add_requirement(ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory))
    course.add_requirement(ProgramRequirement("83999", 2, Semester.FALL, ReqType.Elective))

    service._selected_programs = ["83101"]   # 83999 is NOT selected

    sched = _make_schedule(fall, course, date(2026, 2, 1))

    mock_engine = MagicMock()
    mock_engine.iterPeriodResults.return_value = iter([_make_result(fall, [sched])])
    monkeypatch.setattr(service, "_prepare_engine", lambda: (mock_engine, {}))

    list(service.generate_stream())

    result = service.get_period_schedules("FALL_Aleph")
    assert result[0]["programs"] == ["83101"]
    assert "83999" not in result[0]["programs"]


def test_get_period_schedules_one_entry_per_course_per_schedule(service, monkeypatch):
    """Two courses in one schedule → two entries in the result."""
    fall = _make_period(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 3))
    c1 = _make_course("83102", "Physics", "83101")
    c2 = _make_course("83112", "Calculus", "83101")

    sched = ExamSchedule(fall)
    sched.assign(c1, date(2026, 2, 1))
    sched.assign(c2, date(2026, 2, 2))

    mock_engine = MagicMock()
    mock_engine.iterPeriodResults.return_value = iter([_make_result(fall, [sched])])
    monkeypatch.setattr(service, "_prepare_engine", lambda: (mock_engine, {}))

    list(service.generate_stream())

    result = service.get_period_schedules("FALL_Aleph")
    assert len(result) == 2
    numbers = {entry["course_number"] for entry in result}
    assert numbers == {"83102", "83112"}
