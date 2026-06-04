"""
The single contract between every View widget and the Presenter layer.
No View file may import anything from src.algorithm, src.models, or
src.parsers directly — all calls must go through this interface.
"""

from abc import ABC, abstractmethod
from datetime import date


class IAppService(ABC):
    """Abstract Base Class that declares every method the UI is allowed to call."""

    # ------------------------------------------------------------------ #
    # File loading                                                         #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def load_data(self, courses_path: str, dates_path: str, mode: str) -> None:
        """Parse and store course and period files.

        Args:
            courses_path: Absolute path to the courses data file.
            dates_path:   Absolute path to the exam-periods data file.
            mode:         "replace" — clears all existing data before loading.
                          "append"  — merges new data with existing data.

        Raises:
            FileNotFoundError: if either path does not exist.
            ValueError:        if a file is empty or malformed, or mode is unknown.
        """

    # ------------------------------------------------------------------ #
    # Program selection                                                    #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def get_available_programs(self) -> list[dict]:
        """Return every program derived from the loaded courses.

        Returns:
            List of dicts: [{"id": str, "name": str}, ...]
        """

    @abstractmethod
    def select_programs(self, ids: list[str]) -> None:
        """Record the user's program selection.

        Args:
            ids: List of program ID strings.

        Raises:
            ValueError: if any id is not a 5-digit string, or more than 5
                        ids are supplied.
        """

    # ------------------------------------------------------------------ #
    # Course drill-down                                                    #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def get_courses(self, program_id: str) -> list[dict]:
        """Return all courses belonging to a program.

        Returns:
            List of dicts:
            [{"number": str, "name": str, "year": int,
              "semester": str, "type": str, "evaluation": str}, ...]
        """

    # ------------------------------------------------------------------ #
    # Period management                                                    #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def get_periods(self) -> list[dict]:
        """Return all stored exam periods.

        Returns:
            List of dicts:
            [{"id": str, "semester": str, "moed": str,
              "start_date": date, "end_date": date,
              "allowed_days": list[date], "forbidden_days": list[date]}, ...]
        """

    @abstractmethod
    def toggle_day(self, period_id: str, day: date) -> None:
        """Flip a day between allowed and forbidden for the given period.

        Args:
            period_id: Stable identifier returned by get_periods() ("FALL_Aleph", …).
            day:       The date to toggle.

        Raises:
            ValueError: if period_id is not found.
        """

    @abstractmethod
    def shift_period(self, period_id: str, start: date, end: date) -> None:
        """Change the date range of a period.

        Args:
            period_id: Stable identifier returned by get_periods().
            start:     New start date (must be strictly before end).
            end:       New end date.

        Raises:
            ValueError: if start >= end, or period_id is not found.
        """

    # ------------------------------------------------------------------ #
    # Schedule generation                                                  #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def generate(self) -> int:
        """Run the full blocking generation (backward-compatible).

        Calls generateAll() and waits for every period before returning.
        Used for export and testing. Always called from a background thread.

        Returns:
            Total number of combined schedules produced.

        Raises:
            ValueError: if no programs have been selected.
        """

    @abstractmethod
    def generate_stream(self):
        """Streaming generation — yields one period at a time.

        A generator that wraps engine.iterPeriodResults(). For each period
        that finishes it stores the result in the per-period cache and
        yields (period_id, schedules) so the caller can emit a signal.

        When the generator is exhausted all periods are done, the Combiner
        has run, and self._results is populated for normal navigation.

        Always called from GenerateWorker, never on the main thread.

        Yields:
            tuple[str, list]: (period_id, list_of_ExamSchedule_for_that_period)

        Raises:
            ValueError: if no programs have been selected.
        """

    @abstractmethod
    def get_period_ids(self) -> list[str]:
        """Return the period ids that have results in the cache so far.

        Returns:
            List of period id strings in arrival order, e.g. ["FALL_Aleph", "FALL_Bet"]
        """

    @abstractmethod
    def get_period_schedules(self, period_id: str) -> list[dict]:
        """Return formatted schedules for one period from the streaming cache.

        Used by the Output screen to display a period's results while
        generation is still in progress.

        Returns:
            List of schedule dicts identical in structure to get_schedule().

        Raises:
            KeyError: if period_id is not yet in the cache.
        """

    @abstractmethod
    def get_schedule_count(self, period_id: str | None = None) -> int:
        """Return the total number of combined schedules or the count for one period.

        Args:
            period_id: Optional stable period ID to query a single period.

        Returns:
            Total combined schedule count if period_id is None, otherwise the
            number of schedules available for the requested period.
        """

    @abstractmethod
    def get_schedule_batch(self, start: int, limit: int) -> list[list[dict]]:
        """Return a page of flattened schedules for the output calendar.

        Args:
            start: Zero-based index of the first schedule to return.
            limit: Maximum number of schedules to return.

        Returns:
            List of schedules. Each schedule is a list of exam dictionaries.

        Raises:
            IndexError: if start is negative.
            ValueError: if limit is negative.
        """

    @abstractmethod
    def get_schedule(self, index: int) -> dict:
        """Return one schedule by index.

        Returns:
            Nested dict:
            {
              semester_str: {
                moed_str: [
                  {
                    "course_number": str,
                    "course_name":   str,
                    "type":          str,   # "Obligatory" | "Elective"
                    "programs":      list[str],
                    "exam_date":     date,
                  },
                  ...
                ]
              }
            }

        Raises:
            IndexError: if index is out of range.
        """

    # ------------------------------------------------------------------ #
    # Export                                                               #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def export_schedule(self, index: int, path: str) -> None:
        """Write a single schedule to disk.

        Args:
            index: Index into the results list.
            path:  Output file path chosen by the user.

        Raises:
            IndexError:  if index is out of range.
            IOError:     if the file cannot be written.
        """

    @abstractmethod
    def navigate(self, period_id: str, direction: int) -> dict:
        """Move the current schedule index for one period only.

        Args:
            period_id: Stable period ID ("FALL_Aleph", etc.).
            direction: +1 to advance, -1 to rewind.

        Returns:
            Dict with the updated period_id, index, and schedule data.

        Raises:
            IndexError: if navigation goes out of bounds.
            ValueError: if the period_id is unknown.
        """

    @abstractmethod
    def export_current(self, path: str) -> None:
        """Export the current schedule from each period into one combined file."""
