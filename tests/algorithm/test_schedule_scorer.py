from datetime import date

import pytest

from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.models.program_requirement import ProgramRequirement
from src.models.enums import Evaluation, Semester, Moed, ReqType
from src.models.schedule_score import ScheduleScore
from src.algorithm.schedule_scorer import ScheduleScorer


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_course(name: str, course_id: str, program_id: str, year: int) -> Course:
    course = Course(name, course_id, "Prof. X", Evaluation.Exam)
    course.add_requirement(
        ProgramRequirement(program_id, year, Semester.FALL, ReqType.Obligatory)
    )
    return course


def _make_cross_period_schedule(assignments: list[tuple]) -> ExamSchedule:
    """
    assignments: list of (ExamPeriod, Course, date)
    Returns a merged cross-period ExamSchedule.
    """
    schedules = []
    for period, course, exam_date in assignments:
        s = ExamSchedule(period)
        s.assign(course, exam_date)
        schedules.append(s)

    merged = schedules[0]
    for s in schedules[1:]:
        merged = merged.merge(s)
    return merged


FALL = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 3, 31))
PROGRAM = "83101"


# ------------------------------------------------------------------
# ScheduleScore dataclass
# ------------------------------------------------------------------

def test_schedule_score_defaults():
    score = ScheduleScore()
    assert score.avg_gap == 0.0
    assert score.min_gap == 0
    assert score.spread == 0
    assert score.collisions == 0
    assert score.max_per_day == 0


def test_schedule_score_custom_values():
    score = ScheduleScore(avg_gap=7.5, min_gap=3, spread=21, collisions=1, max_per_day=2)
    assert score.avg_gap == 7.5
    assert score.min_gap == 3
    assert score.spread == 21
    assert score.collisions == 1
    assert score.max_per_day == 2


# ------------------------------------------------------------------
# ScheduleScorer.compute_avg_gap — basic cases
# ------------------------------------------------------------------

def test_avg_gap_two_exams():
    """Two exams 7 days apart → avg_gap = 7.0."""
    c1 = _make_course("Physics 1", "101", PROGRAM, year=1)
    c2 = _make_course("Calculus 1", "102", PROGRAM, year=1)

    schedule = _make_cross_period_schedule([
        (FALL, c1, date(2026, 2, 3)),
        (FALL, c2, date(2026, 2, 10)),
    ])

    scorer = ScheduleScorer()
    assert scorer.compute_avg_gap(schedule, [PROGRAM]) == 7.0


def test_avg_gap_three_exams():
    """Three exams with gaps of 7 and 14 days → avg_gap = 10.5."""
    c1 = _make_course("Physics 1",    "101", PROGRAM, year=1)
    c2 = _make_course("Calculus 1",   "102", PROGRAM, year=1)
    c3 = _make_course("Intro to CS",  "103", PROGRAM, year=1)

    schedule = _make_cross_period_schedule([
        (FALL, c1, date(2026, 2, 3)),
        (FALL, c2, date(2026, 2, 10)),
        (FALL, c3, date(2026, 2, 24)),
    ])

    scorer = ScheduleScorer()
    assert scorer.compute_avg_gap(schedule, [PROGRAM]) == 10.5


def test_avg_gap_returns_zero_for_single_exam():
    """A single exam produces no gaps → avg_gap = 0.0."""
    c1 = _make_course("Physics 1", "101", PROGRAM, year=1)

    schedule = _make_cross_period_schedule([
        (FALL, c1, date(2026, 2, 3)),
    ])

    scorer = ScheduleScorer()
    assert scorer.compute_avg_gap(schedule, [PROGRAM]) == 0.0


def test_avg_gap_empty_schedule():
    """An empty schedule produces avg_gap = 0.0."""
    schedule = ExamSchedule(None)
    scorer = ScheduleScorer()
    assert scorer.compute_avg_gap(schedule, [PROGRAM]) == 0.0


# ------------------------------------------------------------------
# ScheduleScorer.compute_avg_gap — year isolation
# ------------------------------------------------------------------

def test_avg_gap_separates_years():
    """
    Year 1 exams and year 2 exams are treated independently.
    Gaps are not computed across year boundaries.
    """
    c1 = _make_course("Physics 1",  "101", PROGRAM, year=1)
    c2 = _make_course("Calculus 1", "102", PROGRAM, year=1)
    c3 = _make_course("Algorithms", "201", PROGRAM, year=2)

    schedule = _make_cross_period_schedule([
        (FALL, c1, date(2026, 2, 3)),   # year 1
        (FALL, c2, date(2026, 2, 10)),  # year 1 — gap 7
        (FALL, c3, date(2026, 2, 20)),  # year 2 — no cross-year gap
    ])

    scorer = ScheduleScorer()
    # Only one gap: 7 days (within year 1)
    assert scorer.compute_avg_gap(schedule, [PROGRAM]) == 7.0


# ------------------------------------------------------------------
# ScheduleScorer.compute_avg_gap — multiple programs
# ------------------------------------------------------------------

def test_avg_gap_multiple_programs():
    """Gaps from two programs are combined into one average."""
    PROGRAM_B = "83102"

    c1 = _make_course("Physics 1",  "101", PROGRAM,   year=1)
    c2 = _make_course("Calculus 1", "102", PROGRAM,   year=1)
    c3 = _make_course("Networks",   "201", PROGRAM_B, year=1)
    c4 = _make_course("OS",         "202", PROGRAM_B, year=1)

    schedule = _make_cross_period_schedule([
        (FALL, c1, date(2026, 2, 3)),   # program A gap: 7
        (FALL, c2, date(2026, 2, 10)),
        (FALL, c3, date(2026, 2, 5)),   # program B gap: 14
        (FALL, c4, date(2026, 2, 19)),
    ])

    scorer = ScheduleScorer()
    result = scorer.compute_avg_gap(schedule, [PROGRAM, PROGRAM_B])
    # gaps: [7, 14] → avg = 10.5
    assert result == 10.5


def test_avg_gap_unknown_program_returns_zero():
    """A program with no matching courses contributes no gaps → 0.0."""
    c1 = _make_course("Physics 1", "101", PROGRAM, year=1)
    schedule = _make_cross_period_schedule([(FALL, c1, date(2026, 2, 3))])

    scorer = ScheduleScorer()
    assert scorer.compute_avg_gap(schedule, ["99999"]) == 0.0


# ------------------------------------------------------------------
# ScheduleScorer.compute_avg_gap — duplicate dates
# ------------------------------------------------------------------

def test_avg_gap_ignores_duplicate_dates():
    """
    Two courses on the same day produce a gap of 0 — but deduplication
    ensures only one entry per date per group, so no 0-gap is added.
    """
    c1 = _make_course("Physics 1",  "101", PROGRAM, year=1)
    c2 = _make_course("Calculus 1", "102", PROGRAM, year=1)
    c3 = _make_course("Intro to CS","103", PROGRAM, year=1)

    schedule = _make_cross_period_schedule([
        (FALL, c1, date(2026, 2, 3)),
        (FALL, c2, date(2026, 2, 3)),   # same day as c1
        (FALL, c3, date(2026, 2, 10)),
    ])

    scorer = ScheduleScorer()
    # After dedup: [Feb 3, Feb 10] → gap = 7
    assert scorer.compute_avg_gap(schedule, [PROGRAM]) == 7.0


# ------------------------------------------------------------------
# ScheduleScorer.score
# ------------------------------------------------------------------

def test_score_returns_schedule_score_instance():
    """score() returns a ScheduleScore object."""
    c1 = _make_course("Physics 1",  "101", PROGRAM, year=1)
    c2 = _make_course("Calculus 1", "102", PROGRAM, year=1)

    schedule = _make_cross_period_schedule([
        (FALL, c1, date(2026, 2, 3)),
        (FALL, c2, date(2026, 2, 10)),
    ])

    scorer = ScheduleScorer()
    result = scorer.score(schedule, [PROGRAM])

    assert isinstance(result, ScheduleScore)
    assert result.avg_gap == 7.0
