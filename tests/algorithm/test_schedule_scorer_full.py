from datetime import date

import pytest

from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.models.program_requirement import ProgramRequirement
from src.models.enums import Evaluation, Semester, Moed, ReqType
from src.models.schedule_score import ScheduleScore
from src.algorithm.schedule_scorer import ScheduleScorer
from src.algorithm.calculators.min_days_calculator import MinDaysCalculator
from src.algorithm.calculators.collision_calculator import CollisionCalculator
from src.algorithm.calculators.spread_calculator import SpreadCalculator
from src.algorithm.calculators.daily_cap_calculator import DailyCapCalculator


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

FALL = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 3, 31))
PROGRAM = "83101"


def _make_course(
    name: str,
    course_id: str,
    program_id: str,
    year: int,
    req_type: ReqType = ReqType.Obligatory,
) -> Course:
    course = Course(name, course_id, "Prof. X", Evaluation.Exam)
    course.add_requirement(
        ProgramRequirement(program_id, year, Semester.FALL, req_type)
    )
    return course


def _make_schedule(assignments: list[tuple]) -> ExamSchedule:
    schedules = []
    for period, course, exam_date in assignments:
        s = ExamSchedule(period)
        s.assign(course, exam_date)
        schedules.append(s)

    merged = schedules[0]
    for s in schedules[1:]:
        merged = merged.merge(s)
    return merged


# ------------------------------------------------------------------
# MinDaysCalculator (EP-96)
# ------------------------------------------------------------------

def test_min_gap_two_obligatory_exams():
    """Two obligatory exams 7 days apart → min_gap = 7."""
    c1 = _make_course("Physics 1",  "101", PROGRAM, year=1)
    c2 = _make_course("Calculus 1", "102", PROGRAM, year=1)

    schedule = _make_schedule([
        (FALL, c1, date(2026, 2, 3)),
        (FALL, c2, date(2026, 2, 10)),
    ])

    assert MinDaysCalculator().compute(schedule, [PROGRAM]) == 7


def test_min_gap_picks_smallest_gap():
    """Three exams with gaps 7 and 3 → min_gap = 3."""
    c1 = _make_course("Physics 1",  "101", PROGRAM, year=1)
    c2 = _make_course("Calculus 1", "102", PROGRAM, year=1)
    c3 = _make_course("Intro CS",   "103", PROGRAM, year=1)

    schedule = _make_schedule([
        (FALL, c1, date(2026, 2, 3)),
        (FALL, c2, date(2026, 2, 10)),
        (FALL, c3, date(2026, 2, 13)),
    ])

    assert MinDaysCalculator().compute(schedule, [PROGRAM]) == 3


def test_min_gap_ignores_electives():
    """Elective exams are excluded from min_gap calculation."""
    c_ob = _make_course("Physics 1", "101", PROGRAM, year=1, req_type=ReqType.Obligatory)
    c_el = _make_course("Art",       "999", PROGRAM, year=1, req_type=ReqType.Elective)

    schedule = _make_schedule([
        (FALL, c_ob, date(2026, 2, 3)),
        (FALL, c_el, date(2026, 2, 4)),
    ])

    assert MinDaysCalculator().compute(schedule, [PROGRAM]) == 0


def test_min_gap_single_obligatory_returns_zero():
    c1 = _make_course("Physics 1", "101", PROGRAM, year=1)
    schedule = _make_schedule([(FALL, c1, date(2026, 2, 3))])
    assert MinDaysCalculator().compute(schedule, [PROGRAM]) == 0


def test_min_gap_empty_schedule_returns_zero():
    schedule = ExamSchedule(None)
    assert MinDaysCalculator().compute(schedule, [PROGRAM]) == 0


# ------------------------------------------------------------------
# CollisionCalculator (EP-98)
# ------------------------------------------------------------------

def test_elective_collision_detected():
    """An elective on the same day as an obligatory counts as one collision."""
    c_ob = _make_course("Physics 1", "101", PROGRAM, year=1, req_type=ReqType.Obligatory)
    c_el = _make_course("Art",       "999", PROGRAM, year=1, req_type=ReqType.Elective)

    schedule = _make_schedule([
        (FALL, c_ob, date(2026, 2, 3)),
        (FALL, c_el, date(2026, 2, 3)),
    ])

    assert CollisionCalculator().compute(schedule, [PROGRAM]) == 1


def test_no_elective_collision_when_days_differ():
    c_ob = _make_course("Physics 1", "101", PROGRAM, year=1, req_type=ReqType.Obligatory)
    c_el = _make_course("Art",       "999", PROGRAM, year=1, req_type=ReqType.Elective)

    schedule = _make_schedule([
        (FALL, c_ob, date(2026, 2, 3)),
        (FALL, c_el, date(2026, 2, 10)),
    ])

    assert CollisionCalculator().compute(schedule, [PROGRAM]) == 0


def test_two_elective_collisions():
    """Two electives on different days — only the one that collides counts."""
    c_ob  = _make_course("Physics 1", "101", PROGRAM, year=1, req_type=ReqType.Obligatory)
    c_el1 = _make_course("Art",       "991", PROGRAM, year=1, req_type=ReqType.Elective)
    c_el2 = _make_course("Music",     "992", PROGRAM, year=1, req_type=ReqType.Elective)

    schedule = _make_schedule([
        (FALL, c_ob,  date(2026, 2, 3)),
        (FALL, c_el1, date(2026, 2, 3)),
        (FALL, c_el2, date(2026, 2, 10)),
    ])

    assert CollisionCalculator().compute(schedule, [PROGRAM]) == 1


def test_elective_collisions_empty_schedule():
    schedule = ExamSchedule(None)
    assert CollisionCalculator().compute(schedule, [PROGRAM]) == 0


# ------------------------------------------------------------------
# SpreadCalculator (EP-99)
# ------------------------------------------------------------------

def test_spread_two_obligatory_exams():
    """Spread between Feb 3 and Feb 24 = 21 days."""
    c1 = _make_course("Physics 1",  "101", PROGRAM, year=1)
    c2 = _make_course("Calculus 1", "102", PROGRAM, year=1)

    schedule = _make_schedule([
        (FALL, c1, date(2026, 2, 3)),
        (FALL, c2, date(2026, 2, 24)),
    ])

    assert SpreadCalculator().compute(schedule, [PROGRAM]) == 21


def test_spread_uses_first_and_last_only():
    c1 = _make_course("Physics 1",  "101", PROGRAM, year=1)
    c2 = _make_course("Calculus 1", "102", PROGRAM, year=1)
    c3 = _make_course("Intro CS",   "103", PROGRAM, year=1)

    schedule = _make_schedule([
        (FALL, c1, date(2026, 2, 3)),
        (FALL, c2, date(2026, 2, 10)),
        (FALL, c3, date(2026, 2, 24)),
    ])

    assert SpreadCalculator().compute(schedule, [PROGRAM]) == 21


def test_spread_ignores_electives():
    """Electives outside the obligatory range do not affect spread."""
    c_ob = _make_course("Physics 1", "101", PROGRAM, year=1, req_type=ReqType.Obligatory)
    c_el = _make_course("Art",       "999", PROGRAM, year=1, req_type=ReqType.Elective)

    schedule = _make_schedule([
        (FALL, c_ob, date(2026, 2, 10)),
        (FALL, c_el, date(2026, 3, 20)),
    ])

    assert SpreadCalculator().compute(schedule, [PROGRAM]) == 0


def test_spread_single_exam_returns_zero():
    c1 = _make_course("Physics 1", "101", PROGRAM, year=1)
    schedule = _make_schedule([(FALL, c1, date(2026, 2, 3))])
    assert SpreadCalculator().compute(schedule, [PROGRAM]) == 0


def test_spread_empty_schedule_returns_zero():
    schedule = ExamSchedule(None)
    assert SpreadCalculator().compute(schedule, [PROGRAM]) == 0


# ------------------------------------------------------------------
# DailyCapCalculator (EP-100)
# ------------------------------------------------------------------

def test_max_per_day_single_exam():
    c1 = _make_course("Physics 1", "101", PROGRAM, year=1)
    schedule = _make_schedule([(FALL, c1, date(2026, 2, 3))])
    assert DailyCapCalculator().compute(schedule, [PROGRAM]) == 1


def test_max_per_day_two_on_same_day():
    c1 = _make_course("Physics 1",  "101", PROGRAM, year=1)
    c2 = _make_course("Calculus 1", "102", PROGRAM, year=1)

    schedule = _make_schedule([
        (FALL, c1, date(2026, 2, 3)),
        (FALL, c2, date(2026, 2, 3)),
    ])

    assert DailyCapCalculator().compute(schedule, [PROGRAM]) == 2


def test_max_per_day_picks_busiest_day():
    c1 = _make_course("Physics 1",  "101", PROGRAM, year=1)
    c2 = _make_course("Calculus 1", "102", PROGRAM, year=1)
    c3 = _make_course("Intro CS",   "103", PROGRAM, year=1)

    schedule = _make_schedule([
        (FALL, c1, date(2026, 2, 3)),
        (FALL, c2, date(2026, 2, 3)),
        (FALL, c3, date(2026, 2, 10)),
    ])

    assert DailyCapCalculator().compute(schedule, [PROGRAM]) == 2


def test_max_per_day_empty_schedule():
    schedule = ExamSchedule(None)
    assert DailyCapCalculator().compute(schedule, [PROGRAM]) == 0


# ------------------------------------------------------------------
# ScheduleScorer.compute_scores — full ScheduleScore (EP-102)
# ------------------------------------------------------------------

def test_score_populates_all_fields():
    """compute_scores() fills all five fields of ScheduleScore."""
    c1 = _make_course("Physics 1",  "101", PROGRAM, year=1, req_type=ReqType.Obligatory)
    c2 = _make_course("Calculus 1", "102", PROGRAM, year=1, req_type=ReqType.Obligatory)
    c3 = _make_course("Art",        "999", PROGRAM, year=1, req_type=ReqType.Elective)

    schedule = _make_schedule([
        (FALL, c1, date(2026, 2, 3)),
        (FALL, c2, date(2026, 2, 10)),
        (FALL, c3, date(2026, 2, 10)),
    ])

    result = ScheduleScorer(program_ids=[PROGRAM]).compute_scores(schedule)

    assert isinstance(result, ScheduleScore)
    assert result.avg_gap == 7.0
    assert result.min_gap == 7
    assert result.spread == 7
    assert result.collisions == 1
    assert result.max_per_day == 2


def test_score_empty_schedule_returns_zero_score():
    """An empty schedule produces a zeroed ScheduleScore."""
    schedule = ExamSchedule(None)
    result = ScheduleScorer(program_ids=[PROGRAM]).compute_scores(schedule)

    assert result.avg_gap == 0.0
    assert result.min_gap == 0
    assert result.spread == 0
    assert result.collisions == 0
    assert result.max_per_day == 0
