"""
Inner dependency of AppService.  Persists parsed Course and ExamPeriod
objects to disk so unchanged files are not re-parsed on every startup.

Storage format: pickle (handles enums, date objects, and nested structures
without a custom serialiser).

File location: <project_root>/data/datastore.pkl
"""

import os
import pickle
from pathlib import Path
from datetime import date

from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.constraint_settings import ConstraintSettings


# Resolve the project root once at import time.
_PROJECT_ROOT = Path(__file__).parents[2]
_DEFAULT_PATH = _PROJECT_ROOT / "data" / "datastore.pkl"


class DataStore:
    """Stores courses and periods in memory and syncs them to disk."""

    def __init__(self, path: str | Path | None = None):
        self._path = Path(path) if path else _DEFAULT_PATH
        self._courses: list[Course] = []
        self._periods: list[ExamPeriod] = []
        #Dictionary to map program_id -> full display name
        self._program_names: dict[str, str] = {}
        self._constraint_settings = ConstraintSettings()

    # ------------------------------------------------------------------ #
    # Persistence                                                        #
    # ------------------------------------------------------------------ #

    def save(self) -> None:
        """Serialize current state to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "wb") as program_file:
            #Include the program names mapping in the persisted data
            #dump the entire state as a single dictionary for easier loading later
            pickle.dump({
                "courses": self._courses, 
                "periods": self._periods,
                "program_names": self._program_names, # EP-74: Persist the mapping
                "constraint_settings": self._constraint_settings,
            }, program_file)

    def load(self) -> bool:
        """Deserialize state from disk.

        Returns:
            True  — data was loaded successfully.
            False — no persisted file found (first run or after clear).
        """
        # If the file doesn't exist, we consider it a "clean slate" rather than an error.
        if not self._path.exists():
            return False
        try:
            # Attempt to load the file. If it fails, we catch the exception,
            with open(self._path, "rb") as program_file:
                data = pickle.load(program_file)
            self._courses = data.get("courses", [])
            self._periods = data.get("periods", [])
            self._program_names = data.get("program_names", {}) # Load the program names mapping
            self._constraint_settings = data.get(
                "constraint_settings",
                ConstraintSettings()
            )
            return True
        except Exception:
            # Corrupted file — start fresh rather than crashing.
            self._courses = []
            self._periods = []
            self._program_names = {}
            self._constraint_settings = ConstraintSettings()
            return False

    def clear(self) -> None:
        """Wipe in-memory state and delete the persisted file."""
        self._courses = []
        self._periods = []
        self._program_names = {}
        self._constraint_settings = ConstraintSettings()
        if self._path.exists():
            self._path.unlink()

    # ------------------------------------------------------------------ #
    # Write                                                              #
    # ------------------------------------------------------------------ #

    def set_courses(self, courses: list[Course]) -> None:
        """Replace all stored courses with the provided list."""
        self._courses = list(courses)

    def set_periods(self, periods: list[ExamPeriod]) -> None:
        """Replace all stored periods with the provided list."""
        self._periods = list(periods)

    def set_program_names(self, names: dict[str, str]) -> None:
        """
        Sets the mapping between program IDs and their display names.
        This is typically populated by parsing the programs definition file.
        """
        self._program_names = dict(names)

    def set_constraint_settings(self, settings: ConstraintSettings) -> None:
        """Replace the stored advanced constraint settings after validation."""
        settings.validate()
        self._constraint_settings = settings

    def merge_courses(self, new_courses: list[Course]) -> None:
        """Append courses whose course_id is not already stored."""
        existing_ids = {c.course_id for c in self._courses}
        for course in new_courses:
            if course.course_id not in existing_ids:
                self._courses.append(course)
                existing_ids.add(course.course_id)

    def merge_periods(self, new_periods: list[ExamPeriod]) -> None:
        """Append periods whose (semester, moed) key is not already stored."""
        existing_keys = {(p.semester, p.moed) for p in self._periods}
        for period in new_periods:
            key = (period.semester, period.moed)
            if key not in existing_keys:
                self._periods.append(period)
                existing_keys.add(key)

    # ------------------------------------------------------------------ #
    # Read                                                               #
    # ------------------------------------------------------------------ #

    def get_all_courses(self) -> list[Course]:
        return list(self._courses)

    def get_courses_for_program(self, program_id: str) -> list[Course]:
        return [c for c in self._courses if c.belongsToProgram(program_id)]

    def get_programs(self) -> list[dict]:
        """Return unique programs derived from loaded courses.

        Returns:
            [{"id": str, "name": str}, ...]
            If a display name is available in the program names mapping, it is used.
            Otherwise, falls back to using the program ID as the name.
        """
        # Set comprehension to gather unique program IDs from all course requirements
        program_ids = {req.program_id for c in self._courses for req in c.requirements}
        
        programs: list[dict] = []
        for pid in sorted(program_ids):
            #get the name from the dict, or default to the ID string
            display_name = self._program_names.get(pid, pid)
            programs.append({"id": pid, "name": display_name})
            
        return programs

    def get_periods(self) -> list[ExamPeriod]:
        return list(self._periods)
    
    def get_constraint_settings(self) -> ConstraintSettings:
        """Return the current advanced constraint settings."""
        return self._constraint_settings

    def get_period_by_id(self, period_id: str) -> ExamPeriod | None:
        """Look up a period by its stable string ID ("FALL_Aleph", etc.)."""
        for p in self._periods:
            if _period_id(p) == period_id:
                return p
        return None

    def is_empty(self) -> bool:
        return not self._courses and not self._periods


# ------------------------------------------------------------------ #
# Helper                                                             #
# ------------------------------------------------------------------ #

def _period_id(period: ExamPeriod) -> str:
    """Stable string identifier for a period — delegates to ExamPeriod.period_id."""
    return period.period_id