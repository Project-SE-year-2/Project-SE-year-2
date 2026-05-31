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
        """Run the scheduling engine and store results.

        Always called from a background worker thread, never on the main thread.

        Returns:
            Total number of valid schedules produced.

        Raises:
            ValueError: if no programs have been selected.
        """

    @abstractmethod
    def get_schedule_count(self) -> int:
        """Return the total number of schedules from the last generate() call."""

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
