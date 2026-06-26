from datetime import date
from src.models.exam_schedule import ExamSchedule
from src.algorithm.constraints.i_constraint import IConstraint


class AllGapConstraint(IConstraint):
    """
    Verifies that every cohort's exam sequence — combining both Obligatory and
    Elective courses — respects a minimum gap of K days between consecutive exams.

    A cohort is identified by (program_id, year): all courses whose requirements
    include that program_id and year are collected together, regardless of whether
    they are obligatory or elective.

    The constraint fails if any two adjacent exam dates within a cohort are
    separated by strictly fewer than K days (i.e. delta < K is a violation;
    delta == K is allowed).

    Gaps are measured between calendar dates, not between (date, time_slot) pairs.
    If exams were grouped by (date, time_slot), two same-day exams in different slots
    would fall into separate groups with no adjacent pair to compare - allowing a student
    to face two exams on the same day without triggering the K-day gap requirement.
    """

    def __init__(self, k: int) -> None:
        """
        Parameters
        ----------
        k:
            Minimum required gap in days between any two consecutive exams
            in the same cohort.  Must be a positive integer.
        """
        if k <= 0:
            raise ValueError(f"AllGapConstraint: k must be a positive integer, got {k}")
        self._k = k

    # ------------------------------------------------------------------
    # IConstraint implementation
    # ------------------------------------------------------------------

    def is_satisfied(self, schedule: ExamSchedule) -> bool:
        """
        Return False if any cohort has two consecutive exams closer than K days.

        Steps
        -----
        1. Group all course-date assignments by (program_id, year).
        2. For each cohort, sort exam dates chronologically.
        3. Check every adjacent pair — if the gap is less than K days, fail.
        """
        cohort_dates = self._group_by_cohort(schedule)

        for dates in cohort_dates.values():
            if len(dates) < 2:
                # A single exam cannot violate a gap rule.
                continue

            sorted_dates = sorted(dates)
            for i in range(len(sorted_dates) - 1):
                gap = (sorted_dates[i + 1] - sorted_dates[i]).days
                if gap < self._k:
                    return False

        return True

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _group_by_cohort(self, schedule: ExamSchedule) -> dict[tuple, list[date]]:
        """
        Build a mapping from (program_id, year) to a list of exam dates.

        Both Obligatory and Elective courses are included — the requirement
        type is intentionally ignored so the gap applies to the full exam load
        a student faces in that cohort.
        """
        cohort_dates: dict[tuple, list[date]] = {}

        for course, exam_date in schedule.assignments.items():
            seen_cohorts = set()
            for req in course.requirements:
                key = (req.program_id, req.year)
                if key not in seen_cohorts:
                    seen_cohorts.add(key)
                    cohort_dates.setdefault(key, []).append(exam_date)

        return cohort_dates
