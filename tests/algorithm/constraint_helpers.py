"""
Shared factory helpers for constraint unit tests.

Imported by test_daily_cap_constraint, test_collision_constraint,
test_spread_constraint, and any future constraint test that needs the same
Course / ExamSchedule builders.
"""

from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.program_requirement import ProgramRequirement
from src.models.exam_schedule import ExamSchedule
from src.models.enums import Evaluation, Semester, ReqType, Moed


def make_period() -> ExamPeriod:
    return ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "31-01-2026")


def make_elective_course(course_id: str, program_id: str, year: int = 1) -> Course:
    c = Course(f"Course {course_id}", course_id, "Prof", Evaluation.Exam)
    c.add_requirement(ProgramRequirement(program_id, year, Semester.FALL, ReqType.Elective))
    return c


def make_obligatory_course(course_id: str, program_id: str, year: int = 1) -> Course:
    c = Course(f"Course {course_id}", course_id, "Prof", Evaluation.Exam)
    c.add_requirement(ProgramRequirement(program_id, year, Semester.FALL, ReqType.Obligatory))
    return c


def make_schedule(*assignments: tuple) -> ExamSchedule:
    """Build an ExamSchedule from (course, date) pairs using a shared period."""
    period = make_period()
    sched = ExamSchedule(period)
    for course, exam_date in assignments:
        sched.assign(course, exam_date)
    return sched
