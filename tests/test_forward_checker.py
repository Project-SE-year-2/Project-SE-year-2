import pytest
from datetime import date
from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.models.program_requirement import ProgramRequirement
from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.basic_version_validator import BasicVersionValidator
from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.forward_checker import ForwardChecker
from src.models.enums import Evaluation, Semester, Moed, ReqType

def _setup_checker(courses, programs):
    index = ConstraintIndex()
    index.build(courses, programs)
    base_validator = BasicVersionValidator(index)
    validator = ConstraintValidator(index, base_validator)
    return ForwardChecker(validator), validator

def test_has_viable_assignment_returns_true_when_dates_available():
    """
    Tests that hasViableAssignment returns True when there are enough 
    available dates in the exam period to accommodate all remaining courses 
    without causing scheduling conflicts.
    """
    c1 = Course("C1", "1", "A", "Exam")
    c2 = Course("C2", "2", "B", "Exam")
    
    checker, _ = _setup_checker([c1, c2], ["83101"])
    
    period = ExamPeriod("FALL", "Aleph", "01-01-2026", "02-01-2026")
    period.possible_dates = [date(2026, 1, 1), date(2026, 1, 2)]
    
    schedule = ExamSchedule(period)
    
    assert checker.hasViableAssignment([c1, c2], schedule, period) is True

def test_has_viable_assignment_returns_false_when_no_dates_available():
    """
    Tests that hasViableAssignment returns False when an unassigned obligatory
    course has no valid available dates left because all options conflict with
    currently assigned courses.
    """
    c1 = Course("C1", "1", "A", Evaluation.Exam)
    c1.add_requirement(
        ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory)
    )

    c2 = Course("C2", "2", "B", Evaluation.Exam)
    c2.add_requirement(
        ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory)
    )

    checker, _ = _setup_checker([c1, c2], ["83101"])

    period = ExamPeriod(
        Semester.FALL,
        Moed.Aleph,
        "01-01-2026",
        "01-01-2026"
    )
    period.possible_dates = [date(2026, 1, 1)]

    schedule = ExamSchedule(period)
    schedule.assign(c1, date(2026, 1, 1))

    assert checker.hasViableAssignment([c2], schedule, period) is False

# Tests that empty remaining courses always has a viable assignment.
def test_has_viable_assignment_returns_true_for_empty_remaining():
    checker, _ = _setup_checker([], ["83101"])

    period = ExamPeriod("FALL", "Aleph", "01-01-2026", "01-01-2026")
    period.possible_dates = [date(2026, 1, 1)]

    schedule = ExamSchedule(period)

    assert checker.hasViableAssignment([], schedule, period) is True


def test_has_viable_assignment_returns_false_when_one_remaining_course_blocked():
    """
    Tests that hasViableAssignment returns False when at least one
    remaining obligatory course has no legal available date,
    even if other remaining courses are still assignable.
    """
    c1 = Course("C1", "1", "A", Evaluation.Exam)
    c1.add_requirement(
        ProgramRequirement(
            "83101",
            1,
            Semester.FALL,
            ReqType.Obligatory
        )
    )

    c2 = Course("C2", "2", "B", Evaluation.Exam)
    c2.add_requirement(
        ProgramRequirement(
            "83101",
            1,
            Semester.FALL,
            ReqType.Obligatory
        )
    )

    c3 = Course("C3", "3", "C", Evaluation.Exam)
    c3.add_requirement(
        ProgramRequirement(
            "83108",
            1,
            Semester.FALL,
            ReqType.Obligatory
        )
    )

    checker, _ = _setup_checker([c1, c2, c3], ["83101", "83108"])

    period = ExamPeriod(
        Semester.FALL,
        Moed.Aleph,
        "01-01-2026",
        "01-01-2026"
    )

    period.possible_dates = [
        date(2026, 1, 1)
    ]

    schedule = ExamSchedule(period)
    schedule.assign(c1, date(2026, 1, 1))

    assert checker.hasViableAssignment(
        [c2, c3],
        schedule,
        period
    ) is False