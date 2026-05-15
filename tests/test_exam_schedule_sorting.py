from datetime import date

from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule


# Tests that sortByDate returns assignments in chronological order
# for a schedule that belongs to a single exam period.
def test_sort_by_date_single_period_sorts_assignments_chronologically():
    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "03-02-2026")

    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")
    course3 = Course("Algebra 1", "83120", "Prof. C", "Exam")

    schedule = ExamSchedule(period)

    schedule.assign(course1, date(2026, 2, 3))
    schedule.assign(course2, date(2026, 2, 1))
    schedule.assign(course3, date(2026, 2, 2))

    sorted_items = schedule.sortByDate()

    assert sorted_items == [
        (course2, date(2026, 2, 1)),
        (course3, date(2026, 2, 2)),
        (course1, date(2026, 2, 3)),
    ]


# Tests that sortByDate correctly sorts cross-period schedules
# by semester order, moed order, and finally exam date.
def test_sort_by_date_cross_period_sorts_by_semester_moed_then_date():
    fall_aleph = ExamPeriod("FALL", "Aleph", "01-02-2026", "01-02-2026")
    fall_bet = ExamPeriod("FALL", "Bet", "10-04-2026", "10-04-2026")
    spri_aleph = ExamPeriod("SPRI", "Aleph", "01-07-2026", "01-07-2026")

    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")
    course3 = Course("Algebra 1", "83120", "Prof. C", "Exam")

    schedule1 = ExamSchedule(fall_bet)
    schedule1.assign(course1, date(2026, 4, 10))

    schedule2 = ExamSchedule(spri_aleph)
    schedule2.assign(course2, date(2026, 7, 1))

    schedule3 = ExamSchedule(fall_aleph)
    schedule3.assign(course3, date(2026, 2, 1))

    merged = schedule1.merge(schedule2)
    merged = merged.merge(schedule3)

    sorted_items = merged.sortByDate()

    assert sorted_items == [
        (fall_aleph, course3, date(2026, 2, 1)),
        (fall_bet, course1, date(2026, 4, 10)),
        (spri_aleph, course2, date(2026, 7, 1)),
    ]


# Tests that merge creates a cross-period schedule
# that contains assignments from both original schedules.
def test_merge_combines_assignments_from_multiple_periods():
    fall = ExamPeriod("FALL", "Aleph", "01-02-2026", "01-02-2026")
    spri = ExamPeriod("SPRI", "Aleph", "01-07-2026", "01-07-2026")

    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")

    schedule1 = ExamSchedule(fall)
    schedule1.assign(course1, date(2026, 2, 1))

    schedule2 = ExamSchedule(spri)
    schedule2.assign(course2, date(2026, 7, 1))

    merged = schedule1.merge(schedule2)

    sorted_items = merged.sortByDate()

    assert len(sorted_items) == 2

    assert (fall, course1, date(2026, 2, 1)) in sorted_items
    assert (spri, course2, date(2026, 7, 1)) in sorted_items


# Tests that sort_key returns dates in chronological order
# for schedules that belong to a single exam period.
def test_sort_key_single_period():
    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "03-02-2026")

    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")

    schedule = ExamSchedule(period)

    schedule.assign(course1, date(2026, 2, 3))
    schedule.assign(course2, date(2026, 2, 1))

    assert schedule.sort_key == (
        date(2026, 2, 1),
        date(2026, 2, 3),
    )


# Tests that sort_key for cross-period schedules
# preserves the global chronological ordering of all exams.
def test_sort_key_cross_period():
    fall = ExamPeriod("FALL", "Aleph", "01-02-2026", "01-02-2026")
    spri = ExamPeriod("SPRI", "Aleph", "01-07-2026", "01-07-2026")

    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")

    schedule1 = ExamSchedule(spri)
    schedule1.assign(course2, date(2026, 7, 1))

    schedule2 = ExamSchedule(fall)
    schedule2.assign(course1, date(2026, 2, 1))

    merged = schedule1.merge(schedule2)

    assert merged.sort_key == (
        date(2026, 2, 1),
        date(2026, 7, 1),
    )


# Tests that copy creates a completely independent schedule object
# while preserving all original assignments.
def test_copy_creates_independent_schedule():
    period = ExamPeriod("FALL", "Aleph", "01-02-2026", "02-02-2026")

    course1 = Course("Physics 1", "83102", "Prof. A", "Exam")
    course2 = Course("Calculus 1", "83112", "Prof. B", "Exam")

    original = ExamSchedule(period)
    original.assign(course1, date(2026, 2, 1))

    copied = original.copy()

    copied.assign(course2, date(2026, 2, 2))

    assert course2 not in original.assignments
    assert course2 in copied.assignments