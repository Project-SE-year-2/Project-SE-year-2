from datetime import date, datetime, timedelta
from src.models.enums import Semester, Moed

#this class serves as a data container for the period's boundaries.
class ExamPeriod:
    def __init__(self, semester: Semester, moed: Moed, start_date: str | date, end_date: str | date):
        # Initialize the basic identifying information for the period
        self.semester = semester
        self.moed = moed

        # Check if start_date is already a date object, if not, parse it from string
        if isinstance(start_date, str):
            self.start_date = datetime.strptime(start_date.strip(), "%d-%m-%Y").date()
        else:
            self.start_date = start_date

        # Check if end_date is already a date object, if not, parse it from string
        if isinstance(end_date, str):
            self.end_date = datetime.strptime(end_date.strip(), "%d-%m-%Y").date()
        else:
            self.end_date = end_date

        self.possible_dates = []
        # Stage 2.0 — days the user explicitly marked as forbidden via the UI.
        # Kept separate from possible_dates so the GUI can distinguish
        # between file-level restrictions and user-level ones.
        self.forbidden_days: list[date] = []

    # Generates a complete list of every single date within this exam period
    # to return a duplicate of the possible_dates
    def getAvailableDates(self) -> list:
        if self.possible_dates:
            return self.possible_dates

        all_dates = []
        current = self.start_date

        # Iterate through the entire range from start_date to end_date.
        while current <= self.end_date:
            all_dates.append(current)
            current += timedelta(days=1)

        return all_dates

    # ------------------------------------------------------------------ #
    # Stage 2.0 — period editing methods                                  #
    # ------------------------------------------------------------------ #

    def toggle_day(self, day: date) -> None:
        """Flip a day between allowed and forbidden.

        If the day is currently forbidden it becomes allowed again (removed
        from forbidden_days and re-inserted into possible_dates in sorted
        order).  If it is currently allowed it becomes forbidden (added to
        forbidden_days and removed from possible_dates).
        """
        if day in self.forbidden_days:
            self.forbidden_days.remove(day)
            if day not in self.possible_dates:
                self.possible_dates.append(day)
                self.possible_dates.sort()
        else:
            self.forbidden_days.append(day)
            if day in self.possible_dates:
                self.possible_dates.remove(day)

    def shift_dates(self, start: date, end: date) -> None:
        """Change the period's date range.

        Validates that start is strictly before end, then rebuilds
        possible_dates for the new range, removing any forbidden_days
        that now fall outside it.

        Raises:
            ValueError: if start >= end.
        """
        if start >= end:
            raise ValueError(
                f"Start date ({start}) must be strictly before end date ({end})."
            )
        self.start_date = start
        self.end_date = end

        # Drop forbidden days that are now outside the new range
        self.forbidden_days = [
            d for d in self.forbidden_days
            if start <= d <= end and d not in (start, end)
        ]

        # Rebuild possible_dates for the new range
        forbidden_set = set(self.forbidden_days)
        all_dates = []
        current = start
        while current <= end:
            if current not in forbidden_set:
                all_dates.append(current)
            current += timedelta(days=1)
        self.possible_dates = all_dates

    @property
    def period_id(self) -> str:
        """Stable string identifier: '<SEMESTER>_<MOED>' (e.g. 'FALL_Aleph').

        Single source of truth — used by SchedulingEngine, EngineProcess,
        and DataStore so the format never drifts across layers.
        """
        sem  = self.semester.value if hasattr(self.semester, "value") else str(self.semester)
        moed = self.moed.value     if hasattr(self.moed,     "value") else str(self.moed)
        return f"{sem}_{moed}"