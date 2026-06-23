from src.models.exam_schedule import ExamSchedule
from src.models.enums import ReqType
from src.algorithm.constraints.i_partial_constraint import IPartialConstraint


class PartialCollisionConstraint(IPartialConstraint):
    """Prunes partial schedules whose elective collision count already exceeds K."""

    def __init__(self, k: int) -> None:
        """Store the maximum allowed elective exams per (program_id, date) cell."""
        if k < 0:
            raise ValueError(f"PartialCollisionConstraint: k must be non-negative, got {k}")
        self._k = k

    def is_still_valid(self, schedule: ExamSchedule) -> bool:
        """Return False if any (program_id, date) cell already has more than K electives."""
        counts: dict[tuple, int] = {}

        for course, exam_date in schedule.assignments.items():
            for req in course.requirements:
                if req.req_type == ReqType.Elective:
                    key = (req.program_id, exam_date)
                    counts[key] = counts.get(key, 0) + 1

        return all(max(0, count - 1) <= self._k for count in counts.values())