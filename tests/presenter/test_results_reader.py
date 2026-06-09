"""
Standalone tests for ResultsReader.
Covers boundary conditions, error handling, and multi-batch navigation.
"""

import pytest
from datetime import date

from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.models.enums import Evaluation, Semester, Moed
from src.algorithm.period_results_writer import PeriodResultsWriter
from src.presenter.results_reader import ResultsReader


def _make_schedule(period, course, exam_date):
    schedule = ExamSchedule(period)
    schedule.assign(course, exam_date)
    return schedule


def test_get_count_unknown_period(tmp_path):
    """get_count returns 0 for a period that has never been written."""
    reader = ResultsReader(root_path=tmp_path / "results")
    assert reader.get_count("NONEXISTENT_Period") == 0


def test_get_schedule_at_negative_index_raises(tmp_path):
    """Negative index raises IndexError."""
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 3))
    course = Course("C1", "1", "A", Evaluation.Exam)

    writer = PeriodResultsWriter(root_path=tmp_path / "results")
    writer.write_batch("FALL_Aleph", [_make_schedule(period, course, date(2026, 1, 1))])

    reader = ResultsReader(root_path=tmp_path / "results")

    with pytest.raises(IndexError, match="negative"):
        reader.get_schedule_at("FALL_Aleph", -1)


def test_get_schedule_at_out_of_range_raises(tmp_path):
    """Index beyond the total count raises IndexError."""
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 3))
    course = Course("C1", "1", "A", Evaluation.Exam)

    writer = PeriodResultsWriter(root_path=tmp_path / "results")
    writer.write_batch("FALL_Aleph", [_make_schedule(period, course, date(2026, 1, 1))])

    reader = ResultsReader(root_path=tmp_path / "results")

    with pytest.raises(IndexError):
        reader.get_schedule_at("FALL_Aleph", 999)


def test_get_schedule_at_valid_index(tmp_path):
    """Valid index retrieves the correct schedule."""
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 3))
    c1 = Course("C1", "1", "A", Evaluation.Exam)
    c2 = Course("C2", "2", "B", Evaluation.Exam)

    s1 = _make_schedule(period, c1, date(2026, 1, 1))
    s2 = _make_schedule(period, c2, date(2026, 1, 2))

    writer = PeriodResultsWriter(root_path=tmp_path / "results")
    writer.write_batch("FALL_Aleph", [s1, s2])

    reader = ResultsReader(root_path=tmp_path / "results")

    result = reader.get_schedule_at("FALL_Aleph", 0)
    assert any(c.course_id == c1.course_id for c in result.assignments)

    result = reader.get_schedule_at("FALL_Aleph", 1)
    assert any(c.course_id == c2.course_id for c in result.assignments)


def test_get_period_ids(tmp_path):
    """get_period_ids returns all period IDs stored in manifest."""
    period1 = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 3))
    period2 = ExamPeriod(Semester.SPRI, Moed.Bet, date(2026, 6, 1), date(2026, 6, 3))
    c = Course("C1", "1", "A", Evaluation.Exam)

    writer = PeriodResultsWriter(root_path=tmp_path / "results")
    writer.write_batch("FALL_Aleph", [_make_schedule(period1, c, date(2026, 1, 1))])
    writer.write_batch("SPRI_Bet", [_make_schedule(period2, c, date(2026, 6, 1))])

    reader = ResultsReader(root_path=tmp_path / "results")
    ids = reader.get_period_ids()

    assert "FALL_Aleph" in ids
    assert "SPRI_Bet" in ids


def test_multi_batch_navigation(tmp_path):
    """Write 120 schedules across multiple batches and read specific indices."""
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 31))
    course = Course("C1", "1", "A", Evaluation.Exam)

    schedules = []
    for i in range(120):
        day = (i % 28) + 1
        schedules.append(_make_schedule(period, course, date(2026, 1, day)))

    writer = PeriodResultsWriter(root_path=tmp_path / "results")
    writer.write_batch("FALL_Aleph", schedules)

    reader = ResultsReader(root_path=tmp_path / "results")
    assert reader.get_count("FALL_Aleph") == 120

    # Read first, middle, and last schedules
    first = reader.get_schedule_at("FALL_Aleph", 0)
    assert first is not None

    middle = reader.get_schedule_at("FALL_Aleph", 60)
    assert middle is not None

    last = reader.get_schedule_at("FALL_Aleph", 119)
    assert last is not None


def test_missing_manifest_returns_empty(tmp_path):
    """Reader with no manifest file returns 0 for all counts."""
    reader = ResultsReader(root_path=tmp_path / "no_such_dir")
    assert reader.get_count("FALL_Aleph") == 0
    assert reader.get_period_ids() == []
