from datetime import date
from src.models.exam_schedule import ExamSchedule
from src.models.enums import ReqType
from src.algorithm.constraints.i_constraint import IConstraint


class CollisionConstraint(IConstraint):
    """
    Verifies that no single (program_id, date) cell contains more than K
    concurrent elective exam sessions.

    Obligatory requirements are ignored - only courses where a requirement
    carries ReqType.Elective count toward the cap.  A course that is Elective
    in program A but Obligatory in program B contributes only to A's daily
    elective total, not B's.

    Unlike AllGapConstraint, the grouping key is program_id alone (not
    (program_id, year)), so year-1 and year-2 students in the same program
    share the same daily elective budget.

    Elective counts are grouped per (program_id, date), not per (program_id, date, time_slot).
    If time_slot were part of the key, two electives from the same program on the same day
    in different slots would each occupy a separate cell and bypass the daily cap - even
    though the student faces both exams on the same day.
    """

    def __init__(self, k: int) -> None:
        if k < 0:
            raise ValueError(f"CollisionConstraint: k must be a non-negative integer, got {k}")
        self._k = k

    # ------------------------------------------------------------------
    # IConstraint implementation
    # ------------------------------------------------------------------

    def is_satisfied(self, schedule: ExamSchedule) -> bool:
        """Return False if any (program_id, date) cell has more than K elective exams."""
        elective_counts = self._count_electives_by_program_and_date(schedule)
        return all(
            max(0, count - 1) <= self._k
            for count in elective_counts.values()
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _count_electives_by_program_and_date(self, schedule: ExamSchedule) -> dict[tuple, int]:
        """
        Build a mapping from (program_id, date) to the number of elective
        exam sessions scheduled on that date within that program.
        """
        counts: dict[tuple, int] = {}

        for course, exam_date in schedule.assignments.items():
            elective_programs = {
                req.program_id for req in course.requirements
                if req.req_type == ReqType.Elective
            }
            for pid in elective_programs:
                key = (pid, exam_date)
                counts[key] = counts.get(key, 0) + 1

        return counts
