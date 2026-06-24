from datetime import date
from src.models.exam_schedule import ExamSchedule
from src.algorithm.constraints.i_constraint import IConstraint
from src.models.enums import ReqType


class MandatoryGapConstraint(IConstraint):
    """
    Verifies that any two exams categorized as Obligatory belonging to the exact
    same academic program and structural year are separated by strictly more than K calendar days.
    """

    def __init__(self, k: int) -> None:
        """
        Parameters
        ----------
        k:
            Gap parameter. A gap less than or equal to k between consecutive obligatory
            exams in the same cohort will cause the constraint to fail.
            Must be a positive integer.
        """
        if k <= 0:
            raise ValueError(f"MandatoryGapConstraint: k must be a positive integer, got {k}")
        self._k = k

    def is_satisfied(self, schedule: ExamSchedule) -> bool:
        """
        Return False if any pair of obligatory exams for the same cohort
        (program + year) is scheduled with a gap less than or equal to K.
        """
        cohort_dates = self._group_by_cohort(schedule)

        for dates in cohort_dates.values():
            if len(dates) < 2:
                continue

            sorted_dates = sorted(dates)
            for i in range(len(sorted_dates) - 1):
                gap = (sorted_dates[i + 1] - sorted_dates[i]).days
                if gap < self._k:
                    return False

        return True

    def _group_by_cohort(self, schedule: ExamSchedule) -> dict[tuple, list[date]]:
        """
        Build a mapping from (program_id, year) to a list of exam dates,
        ONLY for courses where that specific requirement is Obligatory.
        """
        cohort_dates: dict[tuple, list[date]] = {}

        for course, exam_date in schedule.assignments.items():
            for req in course.requirements:
                if req.req_type == ReqType.Obligatory:
                    key = (req.program_id, req.year)
                    cohort_dates.setdefault(key, []).append(exam_date)

        return cohort_dates
