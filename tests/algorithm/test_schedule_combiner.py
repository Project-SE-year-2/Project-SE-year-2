from datetime import date

from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.algorithm.schedule_combiner import ScheduleCombiner
from src.models.enums import Evaluation, Semester, ReqType,Moed


def _make_schedule(period, course, exam_date):
    schedule = ExamSchedule(period)
    schedule.assign(course, exam_date)
    return schedule


# Tests that combining two periods creates the Cartesian product:
# 2 schedules from one period and 3 schedules from another period
# should create 6 complete schedules.
def test_combiner_creates_cartesian_product():
    fall = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 2))
    spri = ExamPeriod(Semester.SPRI, Moed.Aleph, date(2026, 7, 1), date(2026, 7, 3))

    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)
    course2 = Course("Calculus 1", "83112", "Prof. B", Evaluation.Exam)
    fall_schedules = [
        _make_schedule(fall, course1, date(2026, 2, 1)),
        _make_schedule(fall, course1, date(2026, 2, 2)),
    ]

    spri_schedules = [
        _make_schedule(spri, course2, date(2026, 7, 1)),
        _make_schedule(spri, course2, date(2026, 7, 2)),
        _make_schedule(spri, course2, date(2026, 7, 3)),
    ]

    combiner = ScheduleCombiner()

    combined = combiner.combineSubResults(
        [
            fall_schedules,
            spri_schedules,
        ]
    )

    assert len(combined) == 6


# Tests that every combined schedule contains assignments
# from both original exam periods.
def test_combiner_combined_schedules_contain_all_periods():
    fall = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 1))
    spri = ExamPeriod(Semester.SPRI, Moed.Aleph, date(2026, 7, 1), date(2026, 7, 1))

    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)
    course2 = Course("Calculus 1", "83112", "Prof. B", Evaluation.Exam)

    fall_schedule = _make_schedule(fall, course1, date(2026, 2, 1))
    spri_schedule = _make_schedule(spri, course2, date(2026, 7, 1))

    combiner = ScheduleCombiner()

    combined = combiner.combineSubResults(
        [
            [fall_schedule],
            [spri_schedule],
        ]
    )

    assert len(combined) == 1

    sorted_items = combined[0].sortByDate()

    assert len(sorted_items) == 2

    periods = [item[0] for item in sorted_items]

    assert fall in periods
    assert spri in periods


# Tests that empty period result lists are ignored safely
# and do not break the combining process.
def test_combiner_ignores_empty_period_results():
    fall = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 1))
    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)

    fall_schedule = _make_schedule(fall, course1, date(2026, 2, 1))

    combiner = ScheduleCombiner()

    combined = combiner.combineSubResults(
        [
            [],
            [fall_schedule],
        ]
    )

    assert len(combined) == 1


# Tests that if all sub-results are empty,
# the combiner returns an empty list.
def test_combiner_returns_empty_list_when_all_sub_results_empty():
    combiner = ScheduleCombiner()

    combined = combiner.combineSubResults(
        [
            [],
            [],
        ]
    )

    assert combined == []


# Tests that a single non-empty period result list
# is returned as-is by the combiner.
def test_combiner_single_period_returns_same_schedules():
    fall = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 2))
    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)

    schedule1 = _make_schedule(fall, course1, date(2026, 2, 1))
    schedule2 = _make_schedule(fall, course1, date(2026, 2, 2))

    combiner = ScheduleCombiner()

    combined = combiner.combineSubResults(
        [
            [schedule1, schedule2],
        ]
    )

    assert combined == [schedule1, schedule2]
