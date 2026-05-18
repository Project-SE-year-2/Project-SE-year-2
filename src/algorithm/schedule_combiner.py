from src.models.exam_schedule import ExamSchedule


class ScheduleCombiner:
    """
    Combines per-period BacktrackingSolver results into complete cross-period
    schedules via Cartesian product.

    Each element in sub_results is the list of valid ExamSchedule objects
    produced for one ExamPeriod. The output is every possible combination
    of one assignment from each period — i.e. a complete exam schedule
    covering all courses across all periods.

    Periods with no courses (empty result lists) are skipped.
    """

    def combineSubResults(self, sub_results: list[list[ExamSchedule]]) -> list[ExamSchedule]:
        non_empty = [results for results in sub_results if results]
        if not non_empty:
            return []

        # Seed with the first period's schedules
        combined: list[ExamSchedule] = list(non_empty[0])

        for period_results in non_empty[1:]:
            new_combined: list[ExamSchedule] = []
            for existing in combined:
                for period_sched in period_results:
                    new_combined.append(existing.merge(period_sched))
            combined = new_combined

        return combined
