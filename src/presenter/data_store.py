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


# Resolve the project root once at import time.
_PROJECT_ROOT = Path(__file__).parents[2]
_DEFAULT_PATH = _PROJECT_ROOT / "data" / "datastore.pkl"


class DataStore:
    """Stores courses and periods in memory and syncs them to disk."""

    def __init__(self, path: str | Path | None = None):
        self._path = Path(path) if path else _DEFAULT_PATH
        self._courses: list[Course] = []
        self._periods: list[ExamPeriod] = []

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def save(self) -> None:
        """Serialize current state to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "wb") as f:
            pickle.dump({"courses": self._courses, "periods": self._periods}, f)

    def load(self) -> bool:
        """Deserialize state from disk.

        Returns:
            True  — data was loaded successfully.
            False — no persisted file found (first run or after clear).
        """
        if not self._path.exists():
            return False
        try:
            with open(self._path, "rb") as f:
                data = pickle.load(f)
            self._courses = data.get("courses", [])
            self._periods = data.get("periods", [])
            return True
        except Exception:
            # Corrupted file — start fresh rather than crashing.
            self._courses = []
            self._periods = []
            return False

    def clear(self) -> None:
        """Wipe in-memory state and delete the persisted file."""
        self._courses = []
        self._periods = []
        if self._path.exists():
            self._path.unlink()

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    def set_courses(self, courses: list[Course]) -> None:
        self._courses = list(courses)

    def set_periods(self, periods: list[ExamPeriod]) -> None:
        self._periods = list(periods)

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
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def get_all_courses(self) -> list[Course]:
        return list(self._courses)

    def get_courses_for_program(self, program_id: str) -> list[Course]:
        return [c for c in self._courses if c.belongsToProgram(program_id)]

    def get_programs(self) -> list[dict]:
        """Return unique programs derived from loaded courses.

        Returns:
            [{"id": str, "name": str}, ...] — name equals id (no separate
            program-name field in the course file format).
        """
        seen: set[str] = set()
        programs: list[dict] = []
        for course in self._courses:
            for req in course.requirements:
                if req.program_id not in seen:
                    seen.add(req.program_id)
                    programs.append({"id": req.program_id, "name": req.program_id})
        return programs

    def get_periods(self) -> list[ExamPeriod]:
        return list(self._periods)

    def get_period_by_id(self, period_id: str) -> ExamPeriod | None:
        """Look up a period by its stable string ID ("FALL_Aleph", etc.)."""
        for p in self._periods:
            if _period_id(p) == period_id:
                return p
        return None

    def is_empty(self) -> bool:
        return not self._courses and not self._periods


# ------------------------------------------------------------------ #
# Helper                                                               #
# ------------------------------------------------------------------ #

def _period_id(period: ExamPeriod) -> str:
    """Stable string identifier for a period: "<SEMESTER>_<MOED>"."""
    sem = period.semester.value if hasattr(period.semester, "value") else str(period.semester)
    moed = period.moed.value if hasattr(period.moed, "value") else str(period.moed)
    return f"{sem}_{moed}"
