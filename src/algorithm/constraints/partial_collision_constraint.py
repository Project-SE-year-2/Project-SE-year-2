from src.models.exam_schedule import ExamSchedule
from src.models.enums import ReqType
from src.algorithm.constraints.i_partial_constraint import IPartialConstraint


class PartialCollisionConstraint(IPartialConstraint):
    """Prunes partial schedules whose elective collision count already exceeds K.

    Elective counts are grouped per (program_id, date), not per (program_id, date, time_slot).
    If time_slot were part of the key, two electives from the same program on the same day
    in different slots would each occupy a separate cell and bypass the daily cap - even
    though the student faces both exams on the same day.
    """

    def __init__(self, k: int) -> None:
        """Store the maximum allowed elective exams per (program_id, date) cell."""
        if k < 0:
            raise ValueError(f"PartialCollisionConstraint: k must be non-negative, got {k}")
        self._k = k

    def is_still_valid(self, schedule: ExamSchedule) -> bool:
        """Return False if any (program_id, date) cell already has more than K electives."""
        counts: dict[tuple, int] = {}

        for course, exam_date in schedule.assignments.items():
            elective_programs = {
                req.program_id for req in course.requirements
                if req.req_type == ReqType.Elective
            }
            for pid in elective_programs:
                key = (pid, exam_date)
                counts[key] = counts.get(key, 0) + 1

        return all(max(0, count - 1) <= self._k for count in counts.values())