from datetime import date

from src.models.course import Course
from src.models.exam_placement import ExamPlacement
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.models.room import Room
from src.models.enums import Evaluation, Semester, ReqType, Moed, TimeSlot


# Tests that sortByDate returns assignments in chronological order
# for a schedule that belongs to a single exam period.
def test_sort_by_date_single_period_sorts_assignments_chronologically():
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 3))

    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)
    course2 = Course("Calculus 1", "83112", "Prof. B", Evaluation.Exam)
    course3 = Course("Algebra 1", "83120", "Prof. C", Evaluation.Exam)

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
    fall_aleph = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 1))
    fall_bet = ExamPeriod(Semester.FALL, Moed.Bet, date(2026, 4, 10), date(2026, 4, 10))
    spri_aleph = ExamPeriod(Semester.SPRI, Moed.Aleph, date(2026, 7, 1), date(2026, 7, 1))

    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)
    course2 = Course("Calculus 1", "83112", "Prof. B", Evaluation.Exam)
    course3 = Course("Algebra 1", "83120", "Prof. C", Evaluation.Exam)

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
    fall = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 1))
    spri = ExamPeriod(Semester.SPRI, Moed.Aleph, date(2026, 7, 1), date(2026, 7, 1))

    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)
    course2 = Course("Calculus 1", "83112", "Prof. B", Evaluation.Exam)

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
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 3))

    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)
    course2 = Course("Calculus 1", "83112", "Prof. B", Evaluation.Exam)

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
    fall = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 1))
    spri = ExamPeriod(Semester.SPRI, Moed.Aleph, date(2026, 7, 1), date(2026, 7, 1))

    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)
    course2 = Course("Calculus 1", "83112", "Prof. B", Evaluation.Exam)

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
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 2))

    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)
    course2 = Course("Calculus 1", "83112", "Prof. B", Evaluation.Exam)

    original = ExamSchedule(period)
    original.assign(course1, date(2026, 2, 1))

    copied = original.copy()

    copied.assign(course2, date(2026, 2, 2))

    assert course2 not in original.assignments
    assert course2 in copied.assignments


# Tests that assigning a legacy date is normalized into an ExamPlacement
# while assignments keeps exposing the old Course -> date API.
def test_assign_legacy_date_creates_placement_and_preserves_assignments_api():
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 1))
    course = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)

    schedule = ExamSchedule(period)
    schedule.assign(course, date(2026, 2, 1))

    assert schedule.assignments[course] == date(2026, 2, 1)
    assert schedule.placements[course] == ExamPlacement(date(2026, 2, 1))


# Tests that a full room-based placement is stored internally without breaking
# the compatibility layer that returns only dates.
def test_assign_exam_placement_stores_full_placement():
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 1))
    course = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)
    room = Room(room_id="101", building="4", capacity=80)
    placement = ExamPlacement(
        date=date(2026, 2, 1),
        time_slot=TimeSlot.MORNING,
        rooms=(room,),
    )

    schedule = ExamSchedule(period)
    schedule.assign(course, placement)

    assert schedule.assignments[course] == date(2026, 2, 1)
    assert schedule.placements[course] == placement
    assert schedule.placements[course].total_capacity == 80


# Tests that room-based placements are sorted by date first and then by time slot.
def test_sort_by_date_orders_room_placements_by_time_slot():
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 2))

    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)
    course2 = Course("Calculus 1", "83112", "Prof. B", Evaluation.Exam)
    course3 = Course("Algebra 1", "83120", "Prof. C", Evaluation.Exam)

    schedule = ExamSchedule(period)
    schedule.assign(course1, ExamPlacement(date(2026, 2, 1), TimeSlot.EVENING))
    schedule.assign(course2, ExamPlacement(date(2026, 2, 1), TimeSlot.MORNING))
    schedule.assign(course3, ExamPlacement(date(2026, 2, 2), TimeSlot.AFTERNOON))

    assert schedule.sortByDate() == [
        (course2, date(2026, 2, 1)),
        (course1, date(2026, 2, 1)),
        (course3, date(2026, 2, 2)),
    ]


# Tests that copy preserves full placement objects and remains independent.
def test_copy_preserves_room_based_placements():
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 2))

    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)
    course2 = Course("Calculus 1", "83112", "Prof. B", Evaluation.Exam)
    room = Room(room_id="101", building="4", capacity=80)

    original = ExamSchedule(period)
    original.assign(
        course1,
        ExamPlacement(date(2026, 2, 1), TimeSlot.MORNING, (room,)),
    )

    copied = original.copy()
    copied.assign(course2, ExamPlacement(date(2026, 2, 2), TimeSlot.AFTERNOON))

    assert copied.placements[course1] == original.placements[course1]
    assert course2 not in original.placements
    assert course2 in copied.placements


# Tests that merge keeps full placements available in cross-period schedules.
def test_merge_preserves_cross_period_placements():
    fall = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 1))
    spri = ExamPeriod(Semester.SPRI, Moed.Aleph, date(2026, 7, 1), date(2026, 7, 1))

    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)
    course2 = Course("Calculus 1", "83112", "Prof. B", Evaluation.Exam)
    room = Room(room_id="101", building="4", capacity=80)

    fall_schedule = ExamSchedule(fall)
    fall_placement = ExamPlacement(date(2026, 2, 1), TimeSlot.MORNING, (room,))
    fall_schedule.assign(course1, fall_placement)

    spri_schedule = ExamSchedule(spri)
    spri_placement = ExamPlacement(date(2026, 7, 1), TimeSlot.AFTERNOON)
    spri_schedule.assign(course2, spri_placement)

    merged = fall_schedule.merge(spri_schedule)

    assert merged.assignments[course1] == date(2026, 2, 1)
    assert merged.assignments[course2] == date(2026, 7, 1)
    assert merged.placements[course1] == fall_placement
    assert merged.placements[course2] == spri_placement
