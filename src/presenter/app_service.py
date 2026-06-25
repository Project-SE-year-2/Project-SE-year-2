"""
The single Presenter instance shared by all screens.  Implements IAppService
and wraps the Stage 1.0 engine without modifying it.

Rules enforced here:
  - No PyQt5 imports (this is pure Python logic).
  - generate() is designed to be called from a background thread only.
  - All View communication happens exclusively through IAppService methods.
"""

import os
from pathlib import Path
from datetime import date

from src.presenter.i_app_service import IAppService
from src.presenter.data_store import DataStore, _period_id
from src.parsers.course_parser import CourseFileParser, filter_courses_for_scheduling
from src.parsers.exam_period_file_parser import ExamPeriodFileParser
from src.parsers.programs_name_parser import ProgramsParser
from src.presenter.results_reader import ResultsReader
from src.algorithm.scheduling_algoritem import match_courses_to_periods
from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.exam_period_catalog import ExamPeriodCatalog
from src.algorithm.basic_version_validator import BasicVersionValidator
from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.scheduling_engine import SchedulingEngine
from src.output.schedule_report_writer import ScheduleReportWriter
from src.models.exam_schedule import ExamSchedule
from src.models.constraint_settings import ConstraintSettings
from src.parsers.constraint_settings_loader import ConstraintSettingsLoader
from src.presenter.ranking_query_engine import RankingQueryEngine
from src.algorithm.period_results_writer import BATCH_SIZE


_PROJECT_ROOT = Path(__file__).parents[2]
_DEFAULT_PROGRAM_NAMES_PATH = _PROJECT_ROOT / "data" / "programsName.txt"


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
        self._load_default_program_names()
        self._selected_programs: list[str] = []
        self._results: list[ExamSchedule] = []
        self._last_metadata: dict = {}
        # EP-72 — per-period streaming cache
        # keyed by period_id ("FALL_Aleph", …), values are raw ExamSchedule lists
        self._results_by_period: dict[str, list[ExamSchedule]] = {}
        # EP-82 — file-based per-period navigation
        self._results_writer = None
        self._results_reader = ResultsReader()   # always available for reading from disk
        self._current_indices: dict[str, int] = {}
        # EP-83 — multiprocessing: set to EngineProcess() in main.py to enable
        # two-process architecture. None = legacy single-process mode (used by tests).
        self._engine_process = None
        self._generation_active = False
        # EP-119 - sort order for ranked schedule retrieval
        self._sort_cols: list[str] = []
        self._ranking_engine: RankingQueryEngine | None = None
        # Frozen snapshot: per-period list of (batch_number, index_in_batch) in sorted order.
        # Populated lazily on first ranked access; cleared when sort changes or refresh requested.
        self._sorted_cache: dict[str, list[tuple[int, int]]] = {}
        self._constraint_settings = ConstraintSettings()
        
        self._finished_periods: set[str] = set()
        self._infeasible_periods: set[str] = set()

        # Bug-fix EP-149: regenerate only when the inputs actually changed.
        # Starts dirty so the very first Generate always runs. Set back to clean
        # after a successful generation; flipped to dirty by any input change.
        self._dirty: bool = True

    # ------------------------------------------------------------------ #
    # EP-39 / TASK4 — File loading                                       #
    # ------------------------------------------------------------------ #

    def load_data(self, courses_path: str, dates_path: str, mode: str, programs_path: str = None) -> None:

        # Validate mandatory paths
        self._validate_paths(courses_path, dates_path)
        
        parsed_programs = None
        programs_path = programs_path or self._default_program_names_path()
        # Validate optional programs path
        if programs_path is not None:
            self._validate_paths(programs_path)
            parsed_programs = ProgramsParser.parse(programs_path)

        courses = CourseFileParser().parse(courses_path)
        periods = ExamPeriodFileParser().parse(dates_path)

        if mode == "replace":
            # Overwrite in-memory data — save() below will overwrite the file.
            # No need to delete the file; pickle.dump replaces its contents.
            self._datastore.set_courses(courses)
            self._datastore.set_periods(periods)
            if parsed_programs is not None:
                self._datastore.set_program_names(parsed_programs)

        elif mode == "append":
            self._datastore.merge_courses(courses)
            self._datastore.merge_periods(periods)
            if parsed_programs is not None:
                self._datastore.set_program_names(parsed_programs)

        else:
            raise ValueError(f"Unknown mode '{mode}'. Expected 'replace' or 'append'.")

        self._datastore.save()

        # New input files invalidate any previous run.
        self._mark_dirty()
        self.clear_results()


    def set_constraint_settings(self, settings: ConstraintSettings) -> None:
        """Store active constraint settings for future generation runs.

        Changing the constraints invalidates the previous run, so old results
        are cleared and a fresh generation is required.
        """
        changed = settings != self._constraint_settings
        self._constraint_settings = settings
        if changed:
            self._mark_dirty()
            self.clear_results()

    def set_sort_order(self, sort_cols: list[str]) -> None:
        """Store active ranking columns and clear any frozen ranked snapshots.

        The output screen checks _sort_cols to decide whether to route schedule
        navigation through RankingQueryEngine.  Keeping this as the single
        source of truth preserves the scores.db ranking flow described in the
        technical design.
        """
        self._sort_cols = list(sort_cols)
        self._sorted_cache.clear()

    def refresh_ranked_view(self) -> None:
        """Clear the frozen snapshot so the next navigation re-queries scores.db.
        Called by the 'Refresh View' banner (Task 121) to accept newly written scores."""
        self._sorted_cache.clear()

    def get_sort_order(self) -> list[str]:
        """Return the active sort column list."""
        return list(self._sort_cols)

    def get_constraint_settings(self) -> ConstraintSettings:
        """Return the active constraint settings used by generation."""
        return self._constraint_settings

    # ------------------------------------------------------------------ #
    # EP-149 — stale-result clearing & "needs regeneration" tracking      #
    # ------------------------------------------------------------------ #

    def needs_generation(self) -> bool:
        """True when Generate must actually run the engine again.

        Returns True if an input changed since the last run (dirty) or if there
        are no results on hand yet. When this is False the UI can jump straight
        to the existing results instead of recomputing them.
        """
        return self._dirty or self.get_schedule_count() == 0

    def _mark_dirty(self) -> None:
        """Flag that the inputs changed, so the next Generate re-runs the engine."""
        self._dirty = True

    def clear_results(self) -> None:
        """Drop every trace of the previous run — disk files and in-memory caches.

        Called whenever the inputs change (new files, edited constraints, etc.)
        so the output screen can never show schedules that no longer match the
        current input. Safe to call repeatedly.
        """
        # Stop the background engine if one is running.
        if self._engine_process is not None:
            try:
                self._engine_process.stop()
            except Exception:
                pass

        # Wipe the results directory (batch files + scores.db live under it).
        import shutil
        root = self._results_reader._root
        try:
            if root.exists():
                shutil.rmtree(root, ignore_errors=True)
        except Exception:
            pass

        # Drop the open ranking connection so it doesn't point at a deleted file.
        if self._ranking_engine is not None:
            try:
                self._ranking_engine.close()
            except Exception:
                pass
            self._ranking_engine = None

        # Reset all in-memory navigation/result state.
        self._results = []
        self._results_by_period = {}
        self._last_metadata = {}
        self._current_indices = {}
        self._sorted_cache = {}
        self._finished_periods = set()
        self._infeasible_periods = set()


    def load_constraint_settings_from_file(self, path: str) -> None:
        """Load constraint settings from a text file and store them in the service."""
        settings = ConstraintSettingsLoader.from_file(path)
        self.set_constraint_settings(settings)


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
        if list(ids) != self._selected_programs:
            self._selected_programs = list(ids)
            self._mark_dirty()
        else:
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
        # Editing a period's available days changes what can be scheduled.
        self._mark_dirty()
        self.clear_results()

    def shift_period(self, period_id: str, start: date, end: date) -> None:
        period = self._get_period_or_raise(period_id)
        period.shift_dates(start, end)   # raises ValueError if start >= end
        self._datastore.save()
        # Moving a period's date range invalidates any previous run.
        self._mark_dirty()
        self.clear_results()

    # ------------------------------------------------------------------ #
    # EP-68 / TASK7 — Generation & export                                 #
    # ------------------------------------------------------------------ #

    def _prepare_engine(self):
        """Build and return (engine, scheduling_tasks) — shared by generate() and generate_stream()."""
        if not self._selected_programs:
            raise ValueError("No programs selected. Select at least one program before generating.")

        courses = self._datastore.get_all_courses()
        periods = self._datastore.get_periods()
        settings = self.get_constraint_settings()

        # Guard: room scheduling requires at least one room to be loaded.
        rooms = self._datastore.get_rooms()
        if settings.room_scheduling_enabled and not rooms:
            raise ValueError(
                "Room scheduling is enabled but no rooms have been loaded. "
                "Please load a rooms file before generating."
            )

        valid_courses = filter_courses_for_scheduling(courses, self._selected_programs)
        scheduling_tasks = match_courses_to_periods(valid_courses, periods)

        index = ConstraintIndex()
        index.build(valid_courses, self._selected_programs)

        catalog = ExamPeriodCatalog(periods)
        collision_validator = BasicVersionValidator(index)
        constraint_validator = ConstraintValidator(index, collision_validator)

        # Pass rooms to the engine so SchedulingModeFactory can wire room-aware components.
        engine = SchedulingEngine(
            constraint_validator,
            catalog,
            index,
            settings,
            rooms or None,
        )

        return engine, scheduling_tasks

    def generate(self) -> int:
        """Blocking generation — waits for all periods. Backward-compatible."""
        engine, scheduling_tasks = self._prepare_engine()
        schedules, metadata = engine.generateAll(scheduling_tasks)
        self._results = schedules
        self._last_metadata = metadata
        self._dirty = False   # results now match the current inputs
        return len(schedules)

    # ------------------------------------------------------------------ #
    # EP-72 — Streaming generation                                         #
    # ------------------------------------------------------------------ #

    def generate_stream(self):
        """Generator that yields (period_id, schedules) one period at a time.

        Two modes:
        - File-based mode (_results_writer set): writes each period's
          results to disk in batches of 50, initialises _current_indices
          for per-period navigation, and skips the ScheduleCombiner.
        - Legacy mode (_results_writer is None): same behaviour as before —
          caches results in _results_by_period, runs ScheduleCombiner at the
          end, populates _results for get_schedule() / get_schedule_count().
        """
        engine, scheduling_tasks = self._prepare_engine()
        self._results_by_period = {}
        # Cleanup any previous state before generating
        self._results.clear()
        self._results_by_period.clear()
        self._last_metadata.clear()
        self._current_indices.clear()
        self._sorted_cache.clear()
        self._finished_periods.clear()
        self._infeasible_periods.clear()
        self._generation_active = True

        # ── EP-83: Multiprocessing mode ───────────────────────────────────
        # Engine Process runs solve_to_disk() in a separate OS process.
        # Only lightweight period_id strings cross the process boundary.
        if self._engine_process is not None:
            try:
                self._current_indices = {}
                # Ensure any previous generation run is completely terminated
                self._engine_process.stop()

                # Instantly yield the first period to unblock the UI and trigger OutputScreen
                # to show up immediately in 0ms (it will show loading spinners until data arrives)
                first_pid = next(iter(scheduling_tasks.keys()))
                yield _period_id(first_pid), []

                # Instantly clear all old period results on disk to prevent the OutputScreen
                # from accidentally reading a leftover manifest from a previous run
                from src.algorithm.period_results_writer import PeriodResultsWriter
                writer = PeriodResultsWriter()
                for period in scheduling_tasks.keys():
                    pid = _period_id(period)
                    writer.clear_period(pid)

                self._engine_process.start(engine, scheduling_tasks, self.get_constraint_settings())

                while True:
                    msg = self._engine_process.get_notification()

                    if msg["type"] == "error":
                        raise RuntimeError(msg["message"])

                    if msg["type"] == "all_done":
                        break

                    if msg["type"] == "period_infeasible":
                        pid = msg["period_id"]
                        self._infeasible_periods.add(pid)
                        reason = msg.get("reason", "האילוצים שנבחרו אינם מאפשרים שיבוץ לתקופה זו.")
                        yield pid, [("infeasible", reason)]

                    if msg["type"] in ("period_done", "period_ready"):
                        pid = msg["period_id"]
                        if msg["type"] == "period_done":
                            self._finished_periods.add(pid)
                        self._current_indices.setdefault(pid, 0)
                        yield pid, []
                self._dirty = False   # run finished cleanly → results are current
            finally:
                self._generation_active = False
            return

        # ── EP-82: File-based single-process mode ─────────────────────────
        if self._results_writer is not None:
            try:
                self._current_indices = {}
                for period, courses_dict in scheduling_tasks.items():
                    pid = _period_id(period)
                    engine.solve_to_disk(period, courses_dict, self._results_writer)
                    self._current_indices.setdefault(pid, 0)
                    yield pid, []
                self._dirty = False   # run finished cleanly → results are current
            finally:
                self._generation_active = False
            return

        # ── Legacy mode ───────────────────────────────────────────────────
        # In-memory collection + ScheduleCombiner (used by all existing tests)
        from src.algorithm.schedule_combiner import ScheduleCombiner

        try:
            for period_result in engine.iterPeriodResults(scheduling_tasks):
                pid = _period_id(period_result.period)
                self._results_by_period[pid] = period_result.schedules
                self._last_metadata[period_result.period] = period_result.metadata
                yield pid, period_result.schedules

            all_sub_results = list(self._results_by_period.values())
            combined = ScheduleCombiner().combineSubResults(all_sub_results)
            combined.sort(key=lambda s: s.sort_key)
            self._results = combined
            self._dirty = False   # run finished cleanly → results are current
        finally:
            self._generation_active = False

    def is_generating(self) -> bool:
        """Returns True if the background engine is actively generating schedules."""
        return self._generation_active

    def is_period_generating(self, period_id: str) -> bool:
        """Returns True if a specific period is still actively being generated."""
        if not self._generation_active:
            return False
        return period_id not in self._finished_periods and period_id not in self._infeasible_periods

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

    def get_schedule_count(self, period_id: str | None = None) -> int:
        if period_id is None:
            # Legacy (in-memory) mode: results stored in self._results
            if self._results:
                return len(self._results)
            # Disk-based mode (multiprocessing or file-based): sum per-period counts
            if self._current_indices and self._results_reader:
                return sum(
                    self._results_reader.get_count(pid)
                    for pid in self._current_indices
                )
            return 0
        # Per-period count — disk first
        disk_count = self._results_reader.get_count(period_id)
        if disk_count > 0:
            return disk_count
        # Legacy mode fallback — in-memory per-period results
        if period_id in self._results_by_period:
            return len(self._results_by_period[period_id])
        return 0

    def get_period_schedule(self, period_id: str, index: int) -> list[dict]:
        """Return formatted exam rows for one period at the given local index.

        When a sort order is active and scores.db exists, uses RankingQueryEngine
        to return the schedule ranked at position `index` by the chosen metrics.
        Falls back to sequential disk or in-memory reading otherwise.
        """
        # ── Ranked mode (scores.db + active sort order) ───────────────────────
        if self._sort_cols:
            ranked = self._get_ranked_schedule(period_id, index)
            if ranked is not None:
                return ranked
            # If ranking data is not available yet, keep showing the regular
            # disk/in-memory schedule instead of blanking the output screen.
            if self._sorted_cache.get(period_id):
                return []

        # ── Disk mode ─────────────────────────────────────────────────────────
        disk_count = self._results_reader.get_count(period_id)
        if disk_count > 0:
            safe_index = min(max(0, index), disk_count - 1)
            try:
                schedule = self._results_reader.get_schedule_at(period_id, safe_index)
                return self._format_schedule_rows(schedule)
            except Exception as exc:
                print(f"AppService: disk read failed for {period_id}[{safe_index}]: {exc}")
                return []

        # ── Legacy mode (in-memory per-period results) ────────────────────────
        period_schedules = self._results_by_period.get(period_id)
        if period_schedules:
            safe_index = min(max(0, index), len(period_schedules) - 1)
            try:
                schedule = period_schedules[safe_index]
                return self._format_schedule_rows(schedule)
            except Exception as exc:
                print(f"AppService: format failed for {period_id}[{safe_index}]: {exc}")
                return []

        return []

    def _get_ranked_schedule(self, period_id: str, rank: int) -> list[dict] | None:
        """Return the schedule at the given rank using the current sorted index.

        The sorted index is refreshed when scores.db receives more rows, so
        applying a sort changes only retrieval order while generation, polling,
        and the visible counter continue to progress normally.
        """
        if period_id not in self._sorted_cache:
            if not self._build_sorted_cache(period_id):
                return None
        else:
            engine = self._get_ranking_engine()
            if engine is not None:
                try:
                    if engine.count(period_id) > len(self._sorted_cache[period_id]):
                        self._build_sorted_cache(period_id)
                except Exception:
                    pass
        indices = self._sorted_cache[period_id]
        if rank >= len(indices):
            return None
        batch_number, index_in_batch = indices[rank]
        try:
            linear_index = batch_number * BATCH_SIZE + index_in_batch
            schedule = self._results_reader.get_schedule_at(period_id, linear_index)
            return self._format_schedule_rows(schedule)
        except Exception:
            return None

    def _build_sorted_cache(self, period_id: str) -> bool:
        """Query scores.db for all scored rows in sorted order and store as a frozen index list.

        Only (batch_number, index_in_batch) tuples are loaded - not the full schedule
        data, which stays in batch files on disk. Memory cost is negligible regardless
        of result set size. The cache is refreshed when new scored rows appear.
        """
        engine = self._get_ranking_engine()
        if engine is None:
            return False
        try:
            total = engine.count(period_id)
            if total == 0:
                self._sorted_cache[period_id] = []
                return True
            rows = engine.fetch_window(period_id, self._sort_cols, limit=total, offset=0)
            self._sorted_cache[period_id] = [(r[0], r[1]) for r in rows]
            return True
        except Exception:
            return False

    def _get_ranking_engine(self) -> RankingQueryEngine | None:
        """Return a live RankingQueryEngine, or None if scores.db does not exist."""
        db_path = self._scores_db_path()
        if not db_path.exists():
            if self._ranking_engine is not None:
                self._ranking_engine.close()
                self._ranking_engine = None
            return None
        if self._ranking_engine is None:
            try:
                self._ranking_engine = RankingQueryEngine(db_path)
            except Exception:
                return None
        return self._ranking_engine

    def _scores_db_path(self) -> Path:
        return self._results_reader._root / "scores.db"

    def get_schedule_batch(self, start: int, limit: int) -> list[list[dict]]:
        if start < 0:
            raise IndexError("Schedule batch start index cannot be negative.")
        if limit < 0:
            raise ValueError("Schedule batch limit cannot be negative.")

        # Disk-based mode: in-memory results unavailable but disk results exist
        if not self._results and self._current_indices and self._results_reader:
            return self._get_batch_from_disk(start, limit)

        # Legacy mode: read from in-memory list
        end = min(start + limit, len(self._results))
        return [self._format_schedule_rows(schedule) for schedule in self._results[start:end]]

    def _get_batch_from_disk(self, start: int, limit: int) -> list[list[dict]]:
        """Read a contiguous batch of schedules from disk (multiprocessing / file-based mode).

        Period results are concatenated in the order they appear in _current_indices.
        The caller receives formatted list[dict] rows — same shape as legacy mode.
        """
        result: list[list[dict]] = []
        global_offset = 0

        for pid in self._current_indices:
            count = self._results_reader.get_count(pid)
            # Skip periods that lie entirely before `start`
            if global_offset + count <= start:
                global_offset += count
                continue

            local_start = max(0, start - global_offset)
            to_fetch    = min(limit - len(result), count - local_start)

            for i in range(local_start, local_start + to_fetch):
                try:
                    schedule = self._results_reader.get_schedule_at(pid, i)
                    result.append(self._format_schedule_rows(schedule))
                except Exception:
                    pass   # skip corrupt / missing batch files gracefully

            global_offset += count
            if len(result) >= limit:
                break

        return result

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

    def _format_schedule_rows(self, schedule: ExamSchedule) -> list[dict]:
        """Helper to format a single schedule's courses into a flat list of dicts for table display."""
        result = []
        for (semester, moed), course_date_map in schedule.groupBySemesterAndMoed().items():
            sem_key = semester.value if hasattr(semester, "value") else str(semester)
            moed_key = moed.value if hasattr(moed, "value") else str(moed)

            for course, exam_date in course_date_map.items():
                programs = [
                    req.program_id
                    for req in course.requirements
                    if req.program_id in self._selected_programs
                ]
                req_type = "Obligatory"
                for req in course.requirements:
                    if req.program_id in self._selected_programs:
                        req_type = req.req_type.value
                        break

                result.append({
                    "course_number": course.course_id,
                    "course_name": course.name,
                    "type": req_type,
                    "programs": programs,
                    "exam_date": exam_date,
                    "semester": sem_key,
                    "moed": moed_key,
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
    # EP-82 — Per-period navigation & combined export                     #
    # ------------------------------------------------------------------ #

    def navigate(self, period_id: str, direction: int) -> dict:
        """Move the current schedule index for one period only (±1).

        Other periods are unaffected.  Raises ValueError for an unknown
        period_id and IndexError if the new index would go out of bounds.
        """
        # Ensure the requested period is valid and exists in our navigation state
        if period_id not in self._current_indices:
            raise ValueError(f"Unknown period '{period_id}'.")
        if self._results_reader is None:
            raise RuntimeError("Results reader not initialised.")

        # Calculate the new index and validate boundaries
        new_idx = self._current_indices[period_id] + direction
        count = self._results_reader.get_count(period_id)

        if new_idx < 0 or new_idx >= count:
            raise IndexError(
                f"Schedule index {new_idx} out of range for period "
                f"'{period_id}' (0–{count - 1})."
            )

        # Update the current index and fetch the new schedule from the disk
        self._current_indices[period_id] = new_idx
        schedule = self._results_reader.get_schedule_at(period_id, new_idx)
        return {
            "period_id": period_id,
            "index": new_idx,
            "schedule": self._format_schedule_rows(schedule),
        }

    def navigate_global(self, direction: int) -> dict:
        """Advance or rewind all periods by one combination (odometer carry).

        direction=+1: rightmost period increments; on overflow it resets to 0
                      and the carry propagates left.
        direction=-1: rightmost period decrements; on underflow it is set to
                      its max and the borrow propagates left.

        State is restored before raising so the indices are never corrupted.
        """
        if direction not in (+1, -1):
            raise ValueError(f"direction must be +1 or -1, got {direction}.")
        if not self._current_indices:
            raise ValueError("No periods initialised.")
        if self._results_reader is None:
            raise RuntimeError("Results reader not initialised.")

        period_order = list(self._current_indices.keys())
        snapshot = dict(self._current_indices)

        for pid in reversed(period_order):
            count = self._results_reader.get_count(pid)
            new_idx = self._current_indices[pid] + direction

            if direction == +1:
                if new_idx < count:
                    self._current_indices[pid] = new_idx
                    return dict(self._current_indices)
                self._current_indices[pid] = 0   # carry
            else:
                if new_idx >= 0:
                    self._current_indices[pid] = new_idx
                    return dict(self._current_indices)
                self._current_indices[pid] = count - 1   # borrow

        # Overflow/ underflow - restore and raise
        self._current_indices.update(snapshot)
        raise IndexError(
            "Already at the last combination."
            if direction == +1
            else "Already at the first combination."
        )

    def get_current_combination(self) -> list[dict]:
        """Return the currently selected schedule combination across all periods.

        Reads each active period's schedule from disk (via ``_results_reader``)
        at the index stored in ``_current_indices``, then flattens all the
        per-period rows into one list.

        Raises:
            RuntimeError: when ``_results_reader`` is not initialised (legacy
                          in-memory mode — use ``get_schedule_batch`` instead).
        """
        if self._results_reader is None:
            raise RuntimeError("Results reader not initialised.")

        rows: list[dict] = []
        for period_id, idx in self._current_indices.items():
            if self._results_reader.get_count(period_id) > 0:
                schedule = self._results_reader.get_schedule_at(period_id, idx)
                rows.extend(self._format_schedule_rows(schedule))

        return rows

    def export_by_period_indices(self, period_indices: dict, path: str) -> None:
        """Export one combined schedule built from specific per-period local indices.

        Reads the ExamSchedule at *period_indices[period_id]* for every period
        that has data (disk mode via ResultsReader, or legacy via
        _results_by_period), merges them with ScheduleCombiner, and writes a
        single human-readable report.

        This is the correct export path for the isolated architecture: the caller
        passes _period_indices from the UI (one local index per period tab) and
        the report reflects exactly what is shown on screen.
        """
        from src.algorithm.schedule_combiner import ScheduleCombiner

        schedules_to_merge: list[list] = []

        for period_id, local_index in period_indices.items():
            schedule = None

            # Ranked mode - resolve rank to physical linear index via frozen snapshot
            if self._sort_cols and period_id in self._sorted_cache:
                indices = self._sorted_cache[period_id]
                if 0 <= local_index < len(indices):
                    batch_number, index_in_batch = indices[local_index]
                    linear_index = batch_number * BATCH_SIZE + index_in_batch
                    try:
                        schedule = self._results_reader.get_schedule_at(period_id, linear_index)
                    except Exception as exc:
                        print(f"AppService: export ranked read failed for {period_id}: {exc}")
                if schedule is not None:
                    schedules_to_merge.append([schedule])
                continue

            # Disk mode — batch files written by EngineProcess / file-based mode
            disk_count = self._results_reader.get_count(period_id)
            if disk_count > 0:
                safe_idx = min(max(0, local_index), disk_count - 1)
                try:
                    schedule = self._results_reader.get_schedule_at(period_id, safe_idx)
                except Exception as exc:
                    print(f"AppService: export disk read failed for {period_id}: {exc}")

            # Legacy mode — in-memory per-period results
            if schedule is None and period_id in self._results_by_period:
                period_scheds = self._results_by_period[period_id]
                if period_scheds:
                    safe_idx = min(max(0, local_index), len(period_scheds) - 1)
                    schedule = period_scheds[safe_idx]

            if schedule is not None:
                schedules_to_merge.append([schedule])

        if not schedules_to_merge:
            raise ValueError("No schedule data available to export.")

        combined = ScheduleCombiner().combineSubResults(schedules_to_merge)
        ScheduleReportWriter().write(
            schedules=combined,
            metadata=self._last_metadata,
            programs=self._selected_programs,
            output_path=path,
        )

    def export_current(self, path: str) -> None:
        """Write one combined schedule (from the current index of each period) to disk.

        Each period's currently-selected ExamSchedule is fetched from disk,
        then all periods are merged into a single unified ExamSchedule via
        ScheduleCombiner.combineSubResults, and finally written by
        ScheduleReportWriter so that FALL and SPRING both appear in one file.
        """
        if self._results_reader is None:
            raise RuntimeError("Results reader not initialised.")

        # 1. Collect the currently selected schedule for each period.
        #    combineSubResults expects list[list[ExamSchedule]], so wrap each
        #    single schedule in its own one-element list.
        period_schedules: list[list] = []
        for period_id, idx in self._current_indices.items():
            if self._results_reader.get_count(period_id) > 0:
                schedule = self._results_reader.get_schedule_at(period_id, idx)
                period_schedules.append([schedule])

        if not period_schedules:
            return

        # 2. Merge all per-period schedules into a single unified ExamSchedule.
        from src.algorithm.schedule_combiner import ScheduleCombiner
        combined_schedules = ScheduleCombiner().combineSubResults(period_schedules)

        # 3. Write the merged schedule(s) to disk.
        ScheduleReportWriter().write(
            schedules=combined_schedules,
            metadata=self._last_metadata,
            programs=self._selected_programs,
            output_path=path,
        )

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _validate_paths(self, *paths: str) -> None:
        """Check that each path exists and is not empty. Raises FileNotFoundError or ValueError."""
        for path in paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"File not found: {path}")
            if os.path.getsize(path) == 0:
                raise ValueError(f"File is empty: {path}")

    def _default_program_names_path(self) -> str | None:
        """Return the bundled program-names file path when it exists."""
        if _DEFAULT_PROGRAM_NAMES_PATH.exists():
            return str(_DEFAULT_PROGRAM_NAMES_PATH)
        return None

    def _load_default_program_names(self) -> None:
        """Load bundled program display names so users do not upload them manually."""
        programs_path = self._default_program_names_path()
        if programs_path is None:
            return

        program_names = ProgramsParser.parse(programs_path)
        if program_names:
            self._datastore.set_program_names(program_names)

    def _get_period_or_raise(self, period_id: str):
        period = self._datastore.get_period_by_id(period_id)
        if period is None:
            raise ValueError(f"Period '{period_id}' not found.")
        return period
