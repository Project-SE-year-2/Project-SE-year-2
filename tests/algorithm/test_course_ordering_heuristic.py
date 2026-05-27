import pytest
from src.models.course import Course
from src.models.program_requirement import ProgramRequirement
from src.models.exam_period import ExamPeriod
from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.course_ordering_heuristic import CourseOrderingHeuristic
from src.models.enums import Evaluation, Semester, Moed, ReqType

def test_order_by_most_constrained():
    """
    Tests that orderByMostConstrained properly sorts courses in descending order
    based on the number of potential conflicts they share. Courses involved
    in larger obligatory groups must appear first to enable early pruning.
    """

    # c1 and c2 belong to the same obligatory group
    c1 = Course("C1", "1", "A", Evaluation.Exam)
    c1.add_requirement(
        ProgramRequirement(
            "PROG1",
            1,
            Semester.FALL,
            ReqType.Obligatory
        )
    )

    c2 = Course("C2", "2", "B", Evaluation.Exam)
    c2.add_requirement(
        ProgramRequirement(
            "PROG1",
            1,
            Semester.FALL,
            ReqType.Obligatory
        )
    )

    # c3 belongs to a larger conflict group
    c3 = Course("C3", "3", "C", Evaluation.Exam)
    c3.add_requirement(
        ProgramRequirement(
            "PROG2",
            1,
            Semester.FALL,
            ReqType.Obligatory
        )
    )

    c4 = Course("C4", "4", "D", Evaluation.Exam)
    c4.add_requirement(
        ProgramRequirement(
            "PROG2",
            1,
            Semester.FALL,
            ReqType.Obligatory
        )
    )

    c5 = Course("C5", "5", "E", Evaluation.Exam)
    c5.add_requirement(
        ProgramRequirement(
            "PROG2",
            1,
            Semester.FALL,
            ReqType.Obligatory
        )
    )

    index = ConstraintIndex()
    index.build([c1, c2, c3, c4, c5], ["PROG1", "PROG2"])

    heuristic = CourseOrderingHeuristic(index)

    period = ExamPeriod(
        Semester.FALL,
        Moed.Aleph,
        "01-01-2026",
        "02-01-2026"
    )

    ordered = heuristic.orderByMostConstrained([c1, c2, c3], period)

    # c3 belongs to the larger conflict group and should appear first
    assert ordered[0] == c3

    assert c1 in ordered[1:]
    assert c2 in ordered[1:]
