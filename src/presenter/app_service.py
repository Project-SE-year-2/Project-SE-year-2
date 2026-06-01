"""
The single Presenter instance shared by all screens.  Implements IAppService
and wraps the Stage 1.0 engine without modifying it.

Rules enforced here:
  - No PyQt5 imports (this is pure Python logic).
  - generate() is designed to be called from a background thread only.
  - All View communication happens exclusively through IAppService methods.
"""

import os
from datetime import date

from src.presenter.i_app_service import IAppService
from src.presenter.data_store import DataStore, _period_id
from src.parsers.course_parser import CourseFileParser, filter_courses_for_scheduling
from src.parsers.exam_period_file_parser import ExamPeriodFileParser
from src.algorithm.scheduling_algoritem import match_courses_to_periods
from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.exam_period_catalog import ExamPeriodCatalog
from src.algorithm.basic_version_validator import BasicVersionValidator
from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.scheduling_engine import SchedulingEngine
from src.output.schedule_report_writer import ScheduleReportWriter
from src.models.exam_schedule import ExamSchedule


class AppService(IAppService):
    """Singleton Presenter that wraps the Stage 1.0 engine."""

    _instance: "AppService | None" = None

    # ------------------------------------------------------------------ #
    # Singleton access                                                     #
    # ------------------------------------------------------------------ #

    @classmethod
    def getInstance(cls) -> "AppService":
        if cls._instance is None:
            cls._instance = AppService()
        return cls._instance

    # ------------------------------------------------------------------ #
    # Construction (private — use getInstance())                          #
    # ------------------------------------------------------------------ #

    def __init__(self) -> None:
        self._datastore = DataStore()
        self._datastore.load()          # reload persisted data if it exists
        self._selected_programs: list[str] = []
        self._results: list[ExamSchedule] = []
        self._last_metadata: dict = {}
        # EP-72 — per-period streaming cache
        # keyed by period_id ("FALL_Aleph", …), values are raw ExamSchedule lists
        self._results_by_period: dict[str, list[ExamSchedule]] = {}

    # ------------------------------------------------------------------ #
    # EP-39 / TASK4 — File loading                                        #
    # ------------------------------------------------------------------ #

    def load_data(self, courses_path: str, dates_path: str, mode: str) -> None:
        self._validate_paths(courses_path, dates_path)

        courses = CourseFileParser().parse(courses_path)
        periods = ExamPeriodFileParser().parse(dates_path)

        if mode == "replace":
            # Overwrite in-memory data — save() below will overwrite the file.
            # No need to delete the file; pickle.dump replaces its contents.
            self._datastore.set_courses(courses)
            self._datastore.set_periods(periods)

        elif mode == "append":
            self._datastore.merge_courses(courses)
            self._datastore.merge_periods(periods)

        else:
            raise ValueError(f"Unknown mode '{mode}'. Expected 'replace' or 'append'.")

        self._datastore.save()

    # ------------------------------------------------------------------ #
    # EP-39 / TASK5 — Program & course methods                            #
    # ------------------------------------------------------------------ #

    def get_available_programs(self) -> list[dict]:
        return self._datastore.get_programs()

    def select_programs(self, ids: list[str]) -> None:
        if len(ids) > 5:
            raise ValueError("At most 5 programs can be selected at once.")
        for pid in ids:
            if not (isinstance(pid, str) and len(pid) == 5 and pid.isdigit()):
                raise ValueError(
                    f"Invalid program ID '{pid}'. Must be a 5-digit numeric string."
                )
        self._selected_programs = list(ids)

    def get_courses(self, program_id: str) -> list[dict]:
        courses = self._datastore.get_courses_for_program(program_id)
        result = []
        for course in courses:
            for req in course.requirements:
                if req.program_id == program_id:
                    result.append({
                        "number":     course.course_id,
                        "name":       course.name,
                        "year":       req.year,
                        "semester":   req.semester.value,
                        "type":       req.req_type.value,
                        "evaluation": course.evaluation.value,
                    })
        return result

    # ------------------------------------------------------------------ #
    # EP-39 / TASK6 — Period management                                   #
    # ------------------------------------------------------------------ #

    def get_periods(self) -> list[dict]:
        result = []
        for p in self._datastore.get_periods():
            result.append({
                "id":            _period_id(p),
                "semester":      p.semester.value,
                "moed":          p.moed.value,
                "start_date":    p.start_date,
                "end_date":      p.end_date,
                "allowed_days":  list(p.possible_dates),
                "forbidden_days": list(p.forbidden_days),
            })
        return result

    def toggle_day(self, period_id: str, day: date) -> None:
        period = self._get_period_or_raise(period_id)
        period.toggle_day(day)
        self._datastore.save()

    def shift_period(self, period_id: str, start: date, end: date) -> None:
        period = self._get_period_or_raise(period_id)
        period.shift_dates(start, end)   # raises ValueError if start >= end
        self._datastore.save()

    # ------------------------------------------------------------------ #
    # EP-68 / TASK7 — Generation & export                                 #
    # ------------------------------------------------------------------ #

    def _prepare_engine(self):
        """Build and return (engine, scheduling_tasks) — shared by generate() and generate_stream()."""
        if not self._selected_programs:
            raise ValueError("No programs selected. Select at least one program before generating.")

        courses = self._datastore.get_all_courses()
        periods = self._datastore.get_periods()

        valid_courses = filter_courses_for_scheduling(courses, self._selected_programs)
        scheduling_tasks = match_courses_to_periods(valid_courses, periods)

        index = ConstraintIndex()
        index.build(valid_courses, self._selected_programs)

        catalog = ExamPeriodCatalog(periods)
        collision_validator = BasicVersionValidator(index)
        constraint_validator = ConstraintValidator(index, collision_validator)
        engine = SchedulingEngine(constraint_validator, catalog, index)

        return engine, scheduling_tasks

    def generate(self) -> int:
        """Blocking generation — waits for all periods. Backward-compatible."""
        engine, scheduling_tasks = self._prepare_engine()
        schedules, metadata = engine.generateAll(scheduling_tasks)
        self._results = schedules
        self._last_metadata = metadata
        return len(schedules)

    # ------------------------------------------------------------------ #
    # EP-72 — Streaming generation                                         #
    # ------------------------------------------------------------------ #

    def generate_stream(self):
        """Generator that yields (period_id, schedules) one period at a time.

        Stores each period's results in _results_by_period as they arrive.
        When exhausted, runs the Combiner on the full cache and populates
        _results so get_schedule() / get_schedule_count() work normally.
        """
        from src.algorithm.schedule_combiner import ScheduleCombiner

        engine, scheduling_tasks = self._prepare_engine()
        self._results_by_period = {}

        for period_result in engine.iterPeriodResults(scheduling_tasks):
            pid = _period_id(period_result.period)
            self._results_by_period[pid] = period_result.schedules
            self._last_metadata[period_result.period] = period_result.metadata
            yield pid, period_result.schedules

        # All periods done — combine for navigation and export
        all_sub_results = list(self._results_by_period.values())
        combined = ScheduleCombiner().combineSubResults(all_sub_results)
        combined.sort(key=lambda s: s.sort_key)
        self._results = combined

    def get_period_ids(self) -> list[str]:
        """Return period ids that have results in the cache (in arrival order)."""
        return list(self._results_by_period.keys())

    def get_period_schedules(self, period_id: str) -> list[dict]:
        """Return formatted schedule dicts for one period from the streaming cache."""
        if period_id not in self._results_by_period:
            raise KeyError(f"Period '{period_id}' not yet in cache.")

        result = []
        for schedule in self._results_by_period[period_id]:
            for (semester, moed), course_date_map in schedule.groupBySemesterAndMoed().items():
                sem_key  = semester.value if hasattr(semester, "value") else str(semester)
                moed_key = moed.value     if hasattr(moed,     "value") else str(moed)
                for course, exam_date in course_date_map.items():
                    programs = [
                        req.program_id for req in course.requirements
                        if req.program_id in self._selected_programs
                    ]
                    req_type = "Obligatory"
                    for req in course.requirements:
                        if req.program_id in self._selected_programs:
                            req_type = req.req_type.value
                            break
                    result.append({
                        "course_number": course.course_id,
                        "course_name":   course.name,
                        "type":          req_type,
                        "programs":      programs,
                        "exam_date":     exam_date,
                        "semester":      sem_key,
                        "moed":          moed_key,
                    })
        return result

    def get_schedule_count(self) -> int:
        return len(self._results)

    def get_schedule(self, index: int) -> dict:
        if index < 0 or index >= len(self._results):
            raise IndexError(f"Schedule index {index} is out of range (0–{len(self._results) - 1}).")

        schedule: ExamSchedule = self._results[index]
        result: dict = {}

        for (semester, moed), course_date_map in schedule.groupBySemesterAndMoed().items():
            sem_key  = semester.value if hasattr(semester, "value") else str(semester)
            moed_key = moed.value    if hasattr(moed,     "value") else str(moed)

            if sem_key not in result:
                result[sem_key] = {}
            if moed_key not in result[sem_key]:
                result[sem_key][moed_key] = []

            for course, exam_date in course_date_map.items():
                # Collect every selected program this course belongs to
                programs = [
                    req.program_id
                    for req in course.requirements
                    if req.program_id in self._selected_programs
                ]
                # Use the req_type from the first matching requirement
                req_type = "Obligatory"
                for req in course.requirements:
                    if req.program_id in self._selected_programs:
                        req_type = req.req_type.value
                        break

                result[sem_key][moed_key].append({
                    "course_number": course.course_id,
                    "course_name":   course.name,
                    "type":          req_type,
                    "programs":      programs,
                    "exam_date":     exam_date,
                })

        return result

    def export_schedule(self, index: int, path: str) -> None:
        if index < 0 or index >= len(self._results):
            raise IndexError(f"Schedule index {index} is out of range.")
        schedule = self._results[index]
        writer = ScheduleReportWriter()
        writer.write(
            schedules=[schedule],
            metadata=self._last_metadata,
            programs=self._selected_programs,
            output_path=path,
        )

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _validate_paths(self, *paths: str) -> None:
        for path in paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"File not found: {path}")
            if os.path.getsize(path) == 0:
                raise ValueError(f"File is empty: {path}")

    def _get_period_or_raise(self, period_id: str):
        period = self._datastore.get_period_by_id(period_id)
        if period is None:
            raise ValueError(f"Period '{period_id}' not found.")
        return period
