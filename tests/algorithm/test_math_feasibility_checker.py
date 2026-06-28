import pytest
from datetime import date
from src.algorithm.math_feasibility_checker import MathFeasibilityChecker
from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.constraint_settings import ConstraintSettings
from src.models.program_requirement import ProgramRequirement
from src.models.enums import ReqType, Evaluation, Semester

@pytest.fixture
def base_period():
    return ExamPeriod("FALL_Aleph", Semester.FALL, date(2026, 1, 1), date(2026, 1, 10))

def create_course(course_id, requirements):
    c = Course(course_id, "Test Course", 3.0, Evaluation.Exam)
    for req in requirements:
        c.add_requirement(req)
    return c

def test_math_feasibility_passing(base_period):
    settings = ConstraintSettings(all_gap_enabled=True, all_gap_k=1)
    c1 = create_course("1", [ProgramRequirement("CS", 1, Semester.FALL, ReqType.Obligatory)])
    c2 = create_course("2", [ProgramRequirement("CS", 1, Semester.FALL, ReqType.Obligatory)])
    # 2 courses, 10 days available. Max in cohort is 2.
    # Current formula: (2 - 1) * 1 + 1 = 2 <= 10. Should pass.
    is_feasible, reason = MathFeasibilityChecker.check_feasibility([c1, c2], base_period, settings)
    assert is_feasible is True

def test_math_feasibility_all_gap_failing(base_period):
    settings = ConstraintSettings(all_gap_enabled=True, all_gap_k=10)
    c1 = create_course("1", [ProgramRequirement("CS", 1, Semester.FALL, ReqType.Obligatory)])
    c2 = create_course("2", [ProgramRequirement("CS", 1, Semester.FALL, ReqType.Obligatory)])
    # 2 courses, gap 10. Required days = (2 - 1) * 10 + 1 = 11 > 10.
    is_feasible, reason = MathFeasibilityChecker.check_feasibility([c1, c2], base_period, settings)
    assert is_feasible is False
    assert "A cohort has 2 exams requiring 11 days" in reason

def test_math_feasibility_daily_cap_failing(base_period):
    settings = ConstraintSettings(daily_cap_enabled=True, daily_cap_k=1)
    # 10 available days, cap is 1 -> max 10 courses
    courses = []
    for i in range(12):
        courses.append(create_course(str(i), [ProgramRequirement("CS", 1, Semester.FALL, ReqType.Elective)]))
    
    is_feasible, reason = MathFeasibilityChecker.check_feasibility(courses, base_period, settings)
    assert is_feasible is False
    assert "allows max 10 exams, but 12 are required" in reason

def test_math_feasibility_mandatory_gap_failing(base_period):
    settings = ConstraintSettings(mandatory_gap_enabled=True, mandatory_gap_k=10)
    c1 = create_course("1", [ProgramRequirement("CS", 1, Semester.FALL, ReqType.Obligatory)])
    c2 = create_course("2", [ProgramRequirement("CS", 1, Semester.FALL, ReqType.Obligatory)])
    # 2 mandatory courses, gap 10. Required days = 11 > 10.
    is_feasible, reason = MathFeasibilityChecker.check_feasibility([c1, c2], base_period, settings)
    assert is_feasible is False
    assert "A cohort has 2 mandatory exams requiring 11 days" in reason

def test_math_feasibility_spread_failing(base_period):
    # 10 days available -> max span is 9 days.
    settings = ConstraintSettings(spread_enabled=True, spread_k=10)
    c1 = create_course("1", [ProgramRequirement("CS", 1, Semester.FALL, ReqType.Obligatory)])
    c2 = create_course("2", [ProgramRequirement("CS", 1, Semester.FALL, ReqType.Obligatory)])
    is_feasible, reason = MathFeasibilityChecker.check_feasibility([c1, c2], base_period, settings)
    assert is_feasible is False
    assert "Spread of 10 requested, but period span is only 9" in reason
