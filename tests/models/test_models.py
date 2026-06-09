import pytest
from src.models.course import Course
from src.models.program_requirement import ProgramRequirement
from src.models.enums import Evaluation, Semester, ReqType,Moed

def test_program_requirement_is_obligatory():
    req_ob = ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory)
    req_el = ProgramRequirement("83102", 2, Semester.SPRI, ReqType.Elective)
    assert req_ob.is_obligatory() is True
    assert req_el.is_obligatory() is False

def test_program_requirement_prevents_duplicate_courses():
    req = ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory)
    
    req.add_course("Physics 1")
    req.add_course("Math 1")
    req.add_course("Physics 1") # This is a duplicate, should be ignored

    assert len(req.courses) == 2
    assert "Physics 1" in req.courses
    assert "Math 1" in req.courses

def test_course_belongs_to_program():
    course = Course("Physics 1", "83102", "Prof. O. Some", Evaluation.Exam)
    
    # Add requirements for programs 83101 and 83102
    course.add_requirement(ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory))
    course.add_requirement(ProgramRequirement("83102", 1, Semester.FALL, ReqType.Obligatory))

    assert course.belongsToProgram("83101") is True
    assert course.belongsToProgram("83102") is True
    
    # Test for a program ID that does not exist in the course requirements
    assert course.belongsToProgram("99999") is False


# =====================================================================
# ExamPeriod — toggle_day
# =====================================================================

def test_toggle_day_adds_to_forbidden():
    """Toggling an allowed day moves it to forbidden_days."""
    from datetime import date, timedelta
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 3))
    period.possible_dates = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]

    period.toggle_day(date(2026, 1, 2))

    assert date(2026, 1, 2) in period.forbidden_days
    assert date(2026, 1, 2) not in period.possible_dates


def test_toggle_day_removes_from_forbidden():
    """Toggling a forbidden day restores it to possible_dates."""
    from datetime import date
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 3))
    period.possible_dates = [date(2026, 1, 1), date(2026, 1, 3)]
    period.forbidden_days = [date(2026, 1, 2)]

    period.toggle_day(date(2026, 1, 2))

    assert date(2026, 1, 2) not in period.forbidden_days
    assert date(2026, 1, 2) in period.possible_dates


def test_toggle_day_double_toggle_is_idempotent():
    """Toggling a day twice returns it to its original state."""
    from datetime import date
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 3))
    period.possible_dates = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]

    period.toggle_day(date(2026, 1, 2))
    period.toggle_day(date(2026, 1, 2))

    assert date(2026, 1, 2) not in period.forbidden_days
    assert date(2026, 1, 2) in period.possible_dates


# =====================================================================
# ExamPeriod — shift_dates
# =====================================================================

def test_shift_dates_updates_range():
    """shift_dates replaces start/end and rebuilds possible_dates."""
    from datetime import date
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 5))

    period.shift_dates(date(2026, 2, 1), date(2026, 2, 3))

    assert period.start_date == date(2026, 2, 1)
    assert period.end_date == date(2026, 2, 3)
    assert len(period.possible_dates) == 3


def test_shift_dates_raises_when_start_equals_end():
    """shift_dates raises ValueError when start == end."""
    from datetime import date
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 5))

    with pytest.raises(ValueError):
        period.shift_dates(date(2026, 2, 1), date(2026, 2, 1))


def test_shift_dates_raises_when_start_after_end():
    """shift_dates raises ValueError when start > end."""
    from datetime import date
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 5))

    with pytest.raises(ValueError):
        period.shift_dates(date(2026, 3, 1), date(2026, 2, 1))


def test_shift_dates_drops_forbidden_outside_new_range():
    """Forbidden days that fall outside the new range are removed."""
    from datetime import date
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 10))
    period.forbidden_days = [date(2026, 1, 3), date(2026, 1, 8)]

    period.shift_dates(date(2026, 1, 5), date(2026, 1, 10))

    # Jan 3 is now outside the range, should be dropped
    assert date(2026, 1, 3) not in period.forbidden_days
    # Jan 8 is inside the new range, should be kept
    assert date(2026, 1, 8) in period.forbidden_days


# =====================================================================
# ExamPeriod — getAvailableDates
# =====================================================================

def test_get_available_dates_excludes_forbidden():
    """getAvailableDates returns possible_dates minus forbidden_days."""
    from datetime import date
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 5))
    period.possible_dates = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3),
                             date(2026, 1, 4), date(2026, 1, 5)]
    period.forbidden_days = [date(2026, 1, 2), date(2026, 1, 4)]

    available = period.getAvailableDates()

    assert date(2026, 1, 2) not in available
    assert date(2026, 1, 4) not in available
    assert len(available) == 3


def test_get_available_dates_all_forbidden_returns_empty():
    """When all days are forbidden, getAvailableDates returns an empty list."""
    from datetime import date
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 2))
    period.possible_dates = [date(2026, 1, 1), date(2026, 1, 2)]
    period.forbidden_days = [date(2026, 1, 1), date(2026, 1, 2)]

    assert period.getAvailableDates() == []


def test_get_available_dates_no_possible_dates_uses_range():
    """When possible_dates is empty, getAvailableDates generates from start/end range."""
    from datetime import date
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 3))
    # Leave possible_dates empty (default from __init__)

    available = period.getAvailableDates()
    assert len(available) == 3
    assert date(2026, 1, 1) in available
    assert date(2026, 1, 3) in available


def test_get_available_dates_range_with_forbidden():
    """When possible_dates is empty but forbidden_days has entries, range minus forbidden."""
    from datetime import date
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 5))
    period.forbidden_days = [date(2026, 1, 3)]

    available = period.getAvailableDates()
    assert date(2026, 1, 3) not in available
    assert len(available) == 4


# =====================================================================
# ExamPeriod — period_id
# =====================================================================

def test_period_id_format():
    """period_id returns 'SEMESTER_MOED' format."""
    from datetime import date
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 5))
    assert period.period_id == "FALL_Aleph"


def test_period_id_all_combinations():
    """period_id is correct for all semester/moed combinations."""
    from datetime import date
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    assert ExamPeriod(Semester.FALL, Moed.Bet, date(2026, 1, 1), date(2026, 1, 2)).period_id == "FALL_Bet"
    assert ExamPeriod(Semester.SPRI, Moed.Aleph, date(2026, 6, 1), date(2026, 6, 2)).period_id == "SPRI_Aleph"
    assert ExamPeriod(Semester.SUMM, Moed.Gimel, date(2026, 8, 1), date(2026, 8, 2)).period_id == "SUMM_Gimel"


# =====================================================================
# ExamSchedule — unassign
# =====================================================================

def test_unassign_removes_course():
    """Unassigning a course removes it from the schedule."""
    from datetime import date
    from src.models.exam_schedule import ExamSchedule
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 3))
    course = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)

    schedule = ExamSchedule(period)
    schedule.assign(course, date(2026, 1, 1))
    assert course in schedule.assignments

    schedule.unassign(course)
    assert course not in schedule.assignments


def test_unassign_nonexistent_course_is_safe():
    """Unassigning a course that was never assigned does not raise."""
    from datetime import date
    from src.models.exam_schedule import ExamSchedule
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 3))
    course = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)

    schedule = ExamSchedule(period)
    schedule.unassign(course)  # Should not raise


# =====================================================================
# ExamSchedule — groupBySemesterAndMoed
# =====================================================================

def test_group_by_semester_and_moed_single_period():
    """groupBySemesterAndMoed returns one group for a single-period schedule."""
    from datetime import date
    from src.models.exam_schedule import ExamSchedule
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 3))
    c1 = Course("C1", "1", "A", Evaluation.Exam)
    c2 = Course("C2", "2", "B", Evaluation.Exam)

    schedule = ExamSchedule(period)
    schedule.assign(c1, date(2026, 1, 1))
    schedule.assign(c2, date(2026, 1, 2))

    groups = schedule.groupBySemesterAndMoed()
    assert len(groups) == 1
    key = (Semester.FALL, Moed.Aleph)
    assert key in groups
    assert len(groups[key]) == 2


def test_group_by_semester_and_moed_cross_period():
    """groupBySemesterAndMoed returns multiple groups for a merged schedule."""
    from datetime import date
    from src.models.exam_schedule import ExamSchedule
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    fall = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 2))
    spri = ExamPeriod(Semester.SPRI, Moed.Aleph, date(2026, 6, 1), date(2026, 6, 2))

    c1 = Course("C1", "1", "A", Evaluation.Exam)
    c2 = Course("C2", "2", "B", Evaluation.Exam)

    s1 = ExamSchedule(fall)
    s1.assign(c1, date(2026, 1, 1))

    s2 = ExamSchedule(spri)
    s2.assign(c2, date(2026, 6, 1))

    merged = s1.merge(s2)
    groups = merged.groupBySemesterAndMoed()
    assert len(groups) == 2


# =====================================================================
# ExamSchedule — is_cross_period
# =====================================================================

def test_is_cross_period_false_for_single():
    """is_cross_period is False for a single-period schedule."""
    from datetime import date
    from src.models.exam_schedule import ExamSchedule
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 3))
    schedule = ExamSchedule(period)
    assert schedule.is_cross_period is False


def test_is_cross_period_true_for_merged():
    """is_cross_period is True after merging two schedules."""
    from datetime import date
    from src.models.exam_schedule import ExamSchedule
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    fall = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 2))
    spri = ExamPeriod(Semester.SPRI, Moed.Aleph, date(2026, 6, 1), date(2026, 6, 2))

    s1 = ExamSchedule(fall)
    s2 = ExamSchedule(spri)
    merged = s1.merge(s2)
    assert merged.is_cross_period is True


# =====================================================================
# ExamSchedule — assignments property cross-period
# =====================================================================

def test_assignments_cross_period_returns_flat_dict():
    """assignments property returns flat course→date dict for cross-period schedules."""
    from datetime import date
    from src.models.exam_schedule import ExamSchedule
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    fall = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 2))
    spri = ExamPeriod(Semester.SPRI, Moed.Aleph, date(2026, 6, 1), date(2026, 6, 2))

    c1 = Course("C1", "1", "A", Evaluation.Exam)
    c2 = Course("C2", "2", "B", Evaluation.Exam)

    s1 = ExamSchedule(fall)
    s1.assign(c1, date(2026, 1, 1))
    s2 = ExamSchedule(spri)
    s2.assign(c2, date(2026, 6, 1))

    merged = s1.merge(s2)
    assignments = merged.assignments

    assert c1 in assignments
    assert c2 in assignments
    assert len(assignments) == 2
