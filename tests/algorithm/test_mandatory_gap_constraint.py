import pytest
from datetime import date
from src.models.exam_schedule import ExamSchedule
from src.models.course import Course
from src.models.program_requirement import ProgramRequirement
from src.models.enums import Evaluation, Semester, ReqType, Moed
from src.models.exam_period import ExamPeriod
from src.algorithm.constraints.mandatory_gap_constraint import MandatoryGapConstraint


def _make_course(course_id: str, is_obligatory: bool) -> Course:
    course = Course(f"Course_{course_id}", course_id, "Prof", Evaluation.Exam)
    req_type = ReqType.Obligatory if is_obligatory else ReqType.Elective
    req = ProgramRequirement("CS", 1, Semester.FALL, req_type)
    course.add_requirement(req)
    return course


@pytest.fixture
def schedule() -> ExamSchedule:
    period = ExamPeriod(Semester.FALL, Moed.Aleph, date(2025, 1, 1), date(2025, 1, 31))
    return ExamSchedule(period=period)


def test_mandatory_gap_valid_gap(schedule: ExamSchedule):
    constraint = MandatoryGapConstraint(k=2)

    c1 = _make_course("1", is_obligatory=True)
    c2 = _make_course("2", is_obligatory=True)

    schedule.assign(c1, date(2025, 1, 1))
    schedule.assign(c2, date(2025, 1, 4))  # Gap = 3 > 2 (k)

    assert constraint.is_satisfied(schedule) is True


def test_mandatory_gap_exact_gap(schedule: ExamSchedule):
    constraint = MandatoryGapConstraint(k=2)

    c1 = _make_course("1", is_obligatory=True)
    c2 = _make_course("2", is_obligatory=True)

    schedule.assign(c1, date(2025, 1, 1))
    schedule.assign(c2, date(2025, 1, 3))  # Gap = 2 == 2 (k)

    assert constraint.is_satisfied(schedule) is True

def test_mandatory_gap_invalid_gap(schedule: ExamSchedule):
    constraint = MandatoryGapConstraint(k=2)

    c1 = _make_course("1", is_obligatory=True)
    c2 = _make_course("2", is_obligatory=True)

    schedule.assign(c1, date(2025, 1, 1))
    schedule.assign(c2, date(2025, 1, 2))  # Gap = 1 < 2 (k)

    assert constraint.is_satisfied(schedule) is False


def test_mandatory_gap_ignores_elective(schedule: ExamSchedule):
    constraint = MandatoryGapConstraint(k=2)

    c1 = _make_course("1", is_obligatory=True)
    c2 = _make_course("2", is_obligatory=False)

    schedule.assign(c1, date(2025, 1, 1))
    schedule.assign(c2, date(2025, 1, 3))  # Gap = 2, but c2 is Elective

    assert constraint.is_satisfied(schedule) is True


def test_mandatory_gap_different_cohorts(schedule: ExamSchedule):
    constraint = MandatoryGapConstraint(k=2)

    c1 = Course("C1", "1", "Prof", Evaluation.Exam)
    c1.add_requirement(ProgramRequirement("CS", 1, Semester.FALL, ReqType.Obligatory))

    c2 = Course("C2", "2", "Prof", Evaluation.Exam)
    c2.add_requirement(ProgramRequirement("CS", 2, Semester.FALL, ReqType.Obligatory))  # Different year

    schedule.assign(c1, date(2025, 1, 1))
    schedule.assign(c2, date(2025, 1, 3))  # Gap = 2, but different cohorts

    assert constraint.is_satisfied(schedule) is True


def test_mandatory_gap_multiple_courses(schedule: ExamSchedule):
    constraint = MandatoryGapConstraint(k=2)

    c1 = _make_course("1", is_obligatory=True)
    c2 = _make_course("2", is_obligatory=True)
    c3 = _make_course("3", is_obligatory=True)

    schedule.assign(c1, date(2025, 1, 1))
    schedule.assign(c2, date(2025, 1, 4))
    schedule.assign(c3, date(2025, 1, 7))

    assert constraint.is_satisfied(schedule) is True

    schedule.assign(c3, date(2025, 1, 6))  # Gap from c2 to c3 is 2
    assert constraint.is_satisfied(schedule) is False


def test_mandatory_gap_invalid_k():
    with pytest.raises(ValueError):
        MandatoryGapConstraint(k=0)
