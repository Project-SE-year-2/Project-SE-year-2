from src.models.exam_schedule import ExamSchedule
from src.models.enums import ReqType
from src.algorithm.scoring.i_metric_calculator import IMetricCalculator


class CollisionCalculator(IMetricCalculator):
    """
    Counts the total number of elective-course date collisions across the
    entire schedule.

    For each (program_id, date) cell, every elective exam beyond the first
    is a conflict.  Summing max(0, count - 1) across all cells gives 0 for a
    perfectly spread schedule and grows with each additional overlap.

    Mirror of CollisionConstraint: the constraint asks "does any cell exceed
    threshold K?"; this calculator asks "how many excess electives are there
    in total?"
    """

    def field_name(self) -> str:
        return 'elective_conflicts'

    def compute(self, schedule: ExamSchedule) -> float:
        # Count the number of electives scheduled for each (program_id, date) pair.
        counts: dict[tuple, int] = {}

        # Iterate through all course-date assignments and count electives by (program_id, date).
        for course, exam_date in schedule.assignments.items():
            for req in course.requirements:
                if req.req_type == ReqType.Elective:
                    key = (req.program_id, exam_date)
                    counts[key] = counts.get(key, 0) + 1
                    
        # Each cell with count > 1 contributes (count - 1) conflicts, 
        # since the first elective is not a conflict.
        return float(sum(max(0, count - 1) for count in counts.values()))