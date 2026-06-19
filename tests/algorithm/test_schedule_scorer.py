from datetime import date

from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.models.program_requirement import ProgramRequirement
from src.models.enums import Evaluation, Semester, Moed, ReqType
from src.models.schedule_score import ScheduleMetrics
from src.algorithm.schedule_scorer import ScheduleScorer
from src.algorithm.calculators.avg_days_calculator import AvgDaysCalculator


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_course(name: str, course_id: str, program_id: str, year: int) -> Course:
    course = Course(name, course_id, "Prof. X", Evaluation.Exam)
    course.add_requirement(
        ProgramRequirement(program_id, year, Semester.FALL, ReqType.Obligatory)
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


FALL = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 3, 31))
PROGRAM = "83101"


# ------------------------------------------------------------------
# ScheduleMetrics dataclass
# ------------------------------------------------------------------

def test_schedule_metrics_defaults():
    m = ScheduleMetrics()
    assert m.avg_days_all == 0.0
    assert m.min_days_required == 0
    assert m.span_required == 0
    assert m.elective_conflicts == 0
    assert m.max_exams_per_day == 0


def test_schedule_metrics_custom_values():
    m = ScheduleMetrics(avg_days_all=7.5, min_days_required=3,
                        span_required=21, elective_conflicts=1, max_exams_per_day=2)
    assert m.avg_days_all == 7.5
    assert m.min_days_required == 3
    assert m.span_required == 21
    assert m.elective_conflicts == 1
    assert m.max_exams_per_day == 2


# ------------------------------------------------------------------
# AvgDaysCalculator — EP-97
# ------------------------------------------------------------------

def test_avg_gap_two_exams():
    c1 = _make_course("Physics 1",  "101", PROGRAM, year=1)
    c2 = _make_course("Calculus 1", "102", PROGRAM, year=1)
    schedule = _make_schedule([
        (FALL, c1, date(2026, 2, 3)),
        (FALL, c2, date(2026, 2, 10)),
    ])
    assert AvgDaysCalculator().compute(schedule, [PROGRAM]) == 7.0


def test_avg_gap_three_exams():
    c1 = _make_course("Physics 1",   "101", PROGRAM, year=1)
    c2 = _make_course("Calculus 1",  "102", PROGRAM, year=1)
    c3 = _make_course("Intro to CS", "103", PROGRAM, year=1)
    schedule = _make_schedule([
        (FALL, c1, date(2026, 2, 3)),
        (FALL, c2, date(2026, 2, 10)),
        (FALL, c3, date(2026, 2, 24)),
    ])
    assert AvgDaysCalculator().compute(schedule, [PROGRAM]) == 10.5


def test_avg_gap_single_exam_returns_zero():
    c1 = _make_course("Physics 1", "101", PROGRAM, year=1)
    schedule = _make_schedule([(FALL, c1, date(2026, 2, 3))])
    assert AvgDaysCalculator().compute(schedule, [PROGRAM]) == 0.0


def test_avg_gap_empty_schedule():
    assert AvgDaysCalculator().compute(ExamSchedule(None), [PROGRAM]) == 0.0


def test_avg_gap_separates_years():
    c1 = _make_course("Physics 1",  "101", PROGRAM, year=1)
    c2 = _make_course("Calculus 1", "102", PROGRAM, year=1)
    c3 = _make_course("Algorithms", "201", PROGRAM, year=2)
    schedule = _make_schedule([
        (FALL, c1, date(2026, 2, 3)),
        (FALL, c2, date(2026, 2, 10)),
        (FALL, c3, date(2026, 2, 20)),
    ])
    assert AvgDaysCalculator().compute(schedule, [PROGRAM]) == 7.0


def test_avg_gap_multiple_programs():
    PROGRAM_B = "83102"
    c1 = _make_course("Physics 1",  "101", PROGRAM,   year=1)
    c2 = _make_course("Calculus 1", "102", PROGRAM,   year=1)
    c3 = _make_course("Networks",   "201", PROGRAM_B, year=1)
    c4 = _make_course("OS",         "202", PROGRAM_B, year=1)
    schedule = _make_schedule([
        (FALL, c1, date(2026, 2, 3)),
        (FALL, c2, date(2026, 2, 10)),
        (FALL, c3, date(2026, 2, 5)),
        (FALL, c4, date(2026, 2, 19)),
    ])
    assert AvgDaysCalculator().compute(schedule, [PROGRAM, PROGRAM_B]) == 10.5


def test_avg_gap_unknown_program_returns_zero():
    c1 = _make_course("Physics 1", "101", PROGRAM, year=1)
    schedule = _make_schedule([(FALL, c1, date(2026, 2, 3))])
    assert AvgDaysCalculator().compute(schedule, ["99999"]) == 0.0


def test_avg_gap_ignores_duplicate_dates():
    c1 = _make_course("Physics 1",   "101", PROGRAM, year=1)
    c2 = _make_course("Calculus 1",  "102", PROGRAM, year=1)
    c3 = _make_course("Intro to CS", "103", PROGRAM, year=1)
    schedule = _make_schedule([
        (FALL, c1, date(2026, 2, 3)),
        (FALL, c2, date(2026, 2, 3)),
        (FALL, c3, date(2026, 2, 10)),
    ])
    assert AvgDaysCalculator().compute(schedule, [PROGRAM]) == 7.0


# ------------------------------------------------------------------
# ScheduleScorer.compute_scores — EP-102
# ------------------------------------------------------------------

def test_compute_scores_returns_schedule_metrics():
    c1 = _make_course("Physics 1",  "101", PROGRAM, year=1)
    c2 = _make_course("Calculus 1", "102", PROGRAM, year=1)
    schedule = _make_schedule([
        (FALL, c1, date(2026, 2, 3)),
        (FALL, c2, date(2026, 2, 10)),
    ])
    result = ScheduleScorer(program_ids=[PROGRAM]).compute_scores(schedule)
    assert isinstance(result, ScheduleMetrics)
    assert result.avg_days_all == 7.0


def test_compute_scores_empty_schedule():
    result = ScheduleScorer(program_ids=[PROGRAM]).compute_scores(ExamSchedule(None))
    assert isinstance(result, ScheduleMetrics)
    assert result.avg_days_all == 0.0


def test_compute_scores_no_program_ids_backward_compat():
    """ScheduleScorer() with no args must not raise — backward compatibility."""
    result = ScheduleScorer().compute_scores(ExamSchedule(None))
    assert isinstance(result, ScheduleMetrics)


def test_compute_scores_field_name_mapping():
    """Each calculator's field_name() must match a real ScheduleMetrics attribute."""
    blank = ScheduleMetrics()
    for calc in ScheduleScorer(program_ids=[PROGRAM])._calculators:
        assert hasattr(blank, calc.field_name())
