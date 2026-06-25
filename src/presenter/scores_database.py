"""
scores_database.py
------------------
SQLite-backed storage for schedule quality metrics.

Each row links a schedule (identified by batch_number + index_in_batch inside
that PKL file) to the five metric values computed by ScheduleScorer.

Responsibilities of this module:
  - Define the scores table schema.
  - Create one composite index per metric column for fast ORDER BY queries.
  - Enable WAL journal mode so Engine writes and UI reads do not block each other.
  - Expose a write-only repository API (insert / insert_batch / clear_period).

Ranking queries (SELECT with ORDER BY / LIMIT / OFFSET) live in
RankingQueryEngine, which receives the same db_path and opens its own
read-only connection.
"""

import multiprocessing
import sqlite3
from math import isfinite
from pathlib import Path
from typing import Optional

from src.algorithm.scoring.schedule_metrics import ScheduleMetrics  # noqa: F401 — re-exported for callers


# ---------------------------------------------------------------------------
# ScoresDatabase  — schema + write repository
# ---------------------------------------------------------------------------

class ScoresDatabase:
    """
    Creates and manages scores.db.

    Only the Engine process calls write methods (insert / insert_batch /
    clear_period / mark_done).  The UI process reads via RankingQueryEngine
    using a separate connection opened in WAL read mode.

    The optional queue parameter is a multiprocessing.Queue shared between the
    Engine process and the UI process.  After every successful write the
    database puts a notification event on the queue so that EngineListener
    (running in the UI process) can emit a QSignal without polling.
    """

    def __init__(
        self,
        db_path: Path,
        queue: Optional[multiprocessing.Queue] = None,
    ) -> None:
        """
        Open (or create) the database file and initialise the schema.

        Parameters
        ----------
        db_path:
            Path to the SQLite file.  Created (including parent directories)
            if it does not exist yet.
        queue:
            Optional cross-process communication channel.  When provided,
            insert() and insert_batch() post a "batch_written" event after each
            successful commit so that the UI process is notified immediately
            instead of discovering new rows on the next poll cycle.
            Pass None (default) to disable queue notifications — useful in
            unit tests and in single-process usage.

        check_same_thread=False is required because solve_to_disk() may be
        called from a worker thread inside the Engine process while the main
        Engine thread holds the same connection object.
        """
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        # Store the queue reference; None means "no cross-process notifications".
        self._queue: Optional[multiprocessing.Queue] = queue
        self._enable_wal()
        self._create_scores_table()
        self._migrate()
        self._create_ranking_indexes()

    # ------------------------------------------------------------------
    # WAL configuration
    # ------------------------------------------------------------------

    def _enable_wal(self) -> None:
        """
        Switch the journal mode to WAL (Write-Ahead Logging).

        In WAL mode a writer does not block readers and readers do not block
        writers.  This is essential because the Engine process continuously
        INSERTs rows while the UI process runs ORDER BY / LIMIT queries on
        the same database file.

        SYNCHRONOUS=NORMAL reduces unnecessary fsync calls while still
        guaranteeing that committed data survives an application crash
        (acceptable for ephemeral generation results).
        """
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _create_scores_table(self) -> None:
        """
        Create the scores table if it does not already exist.

        Column layout:

          id              – auto-increment primary key; not used for ranking
                            but useful for debugging and row identity.
          period_id       – string key matching ExamPeriod.period_id
                            (e.g. "fall_a", "spring_b").  All ranking queries
                            filter on this column first.
          batch_number    – which batch_NNNN.pkl file holds the full schedule
                            object (written by PeriodResultsWriter).
          index_in_batch  – position (0-based) inside that pkl list.

          Together (period_id, batch_number, index_in_batch) form a unique
          pointer that ResultsReader can use to load the full ExamSchedule.

          The five metric columns mirror ScheduleMetrics exactly.
        """
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                period_id           TEXT    NOT NULL,
                batch_number        INTEGER NOT NULL,
                index_in_batch      INTEGER NOT NULL,
                min_days_required   REAL    NOT NULL,
                avg_days_all        REAL    NOT NULL,
                elective_conflicts  INTEGER NOT NULL,
                span_required       INTEGER NOT NULL,
                max_exams_per_day   INTEGER NOT NULL,
                avg_room_distance   REAL    NOT NULL DEFAULT 0
            )
        """)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Migration
    # ------------------------------------------------------------------

    def _migrate(self) -> None:
        """
        Add columns introduced after the initial schema without touching existing rows.

        SQLite's ALTER TABLE … ADD COLUMN is non-destructive: existing rows receive
        the column's DEFAULT value.  The operation is a no-op when the column is
        already present (caught via OperationalError), so this method is safe to
        call on both fresh and legacy database files.
        """
        existing = {
            row[1]
            for row in self._conn.execute("PRAGMA table_info(scores)").fetchall()
        }
        if "avg_room_distance" not in existing:
            self._conn.execute(
                "ALTER TABLE scores ADD COLUMN avg_room_distance REAL NOT NULL DEFAULT 0"
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Ranking indexes
    # ------------------------------------------------------------------

    def _create_ranking_indexes(self) -> None:
        """
        Create one composite index per metric column.

        Index structure:  (period_id, <metric_col> <direction>)

        The period_id prefix is mandatory: every ranking query starts with
        WHERE period_id = ?, so including it in the index lets SQLite satisfy
        the entire query (filter + sort + limit) from the B-tree without
        touching individual table rows until the LIMIT is reached.

        Direction matches the natural ORDER BY for that column so that SQLite
        can iterate the index in forward order instead of doing a post-sort:

          DESC  – columns where a higher value is better
                  (min_days_required, avg_days_all, span_required)

          ASC   – columns where a lower value is better
                  (elective_conflicts, max_exams_per_day)

        With 1 M rows and a single-column primary sort, each page fetch of
        1 000 rows resolves in O(log N + 1 000) index lookups rather than
        O(N log N) for a full-table sort.
        """
        index_definitions = [
            # higher-is-better: ORDER BY DESC puts the best schedule first
            ("idx_scores_min_days",    "min_days_required",  "DESC"),
            ("idx_scores_avg_days",    "avg_days_all",       "DESC"),
            ("idx_scores_span",        "span_required",      "DESC"),
            # lower-is-better: ORDER BY ASC puts the best schedule first
            ("idx_scores_conflicts",   "elective_conflicts",  "ASC"),
            ("idx_scores_daily_cap",   "max_exams_per_day",   "ASC"),
            ("idx_scores_room_dist",   "avg_room_distance",   "ASC"),
        ]
        for idx_name, col, direction in index_definitions:
            self._conn.execute(
                f"CREATE INDEX IF NOT EXISTS {idx_name} "
                f"ON scores (period_id, {col} {direction})"
            )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Write repository (Engine-side API)
    # ------------------------------------------------------------------

    def insert(
        self,
        period_id: str,
        batch_number: int,
        index_in_batch: int,
        metrics: ScheduleMetrics,
    ) -> None:
        """
        Persist the metrics for a single schedule.

        Called by solve_to_disk() each time a new schedule is accepted by
        ConstraintChecker and scored by ScheduleScorer.

        After the commit, a "batch_written" event is posted to the queue (if
        one was supplied) so that EngineListener in the UI process wakes up
        and can check whether the new schedule is better than the current
        rank-1 result.
        """
        self._conn.execute(
            """
            INSERT INTO scores
                (period_id, batch_number, index_in_batch,
                 min_days_required, avg_days_all, elective_conflicts,
                 span_required, max_exams_per_day, avg_room_distance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                period_id,
                batch_number,
                index_in_batch,
                self._finite_or_zero(metrics.min_days_required),
                metrics.avg_days_all,
                metrics.elective_conflicts,
                metrics.span_required,
                metrics.max_exams_per_day,
                metrics.avg_room_distance,
            ),
        )
        self._conn.commit()
        if self._queue is not None:
            self._queue.put({"event": "batch_written", "period_id": period_id, "count": 1})

    def insert_batch(
        self,
        period_id: str,
        rows: list[tuple[int, int, ScheduleMetrics]],
    ) -> None:
        """
        Persist metrics for an entire batch in a single transaction.

        rows is a list of (batch_number, index_in_batch, ScheduleMetrics).

        Prefer this over repeated insert() calls when processing a full batch
        at once: one COMMIT is far cheaper than N individual COMMITs.

        A single "batch_written" event is posted after the commit regardless of
        how many rows were inserted — the UI only needs to know that new data
        arrived, not how many rows were added.
        """
        self._conn.executemany(
            """
            INSERT INTO scores
                (period_id, batch_number, index_in_batch,
                 min_days_required, avg_days_all, elective_conflicts,
                 span_required, max_exams_per_day, avg_room_distance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    period_id,
                    batch_num,
                    idx_in_batch,
                    self._finite_or_zero(m.min_days_required),
                    m.avg_days_all,
                    m.elective_conflicts,
                    m.span_required,
                    m.max_exams_per_day,
                    m.avg_room_distance,
                )
                for batch_num, idx_in_batch, m in rows
            ],
        )
        self._conn.commit()
        if self._queue is not None:
            self._queue.put({"event": "batch_written", "period_id": period_id, "count": len(rows)})

    @staticmethod
    def _finite_or_zero(value: float) -> float:
        """Normalize non-finite metric values before they enter scores.db."""
        return float(value) if isfinite(float(value)) else 0.0

    def mark_done(self) -> None:
        """
        Signal the UI process that the Engine has finished generating all schedules.

        Posts an "engine_done" event to the queue so that EngineListener stops
        blocking on queue.get() and emits its engine_done QSignal.  The UI can
        then hide the progress spinner and show a "Complete" badge.

        Called once, after solve_to_disk() (or solve_all_to_disk_round_robin())
        returns for the last period.  Safe to call when no queue is configured
        (no-op in that case).
        """
        if self._queue is not None:
            self._queue.put({"event": "engine_done"})

    def clear_period(self, period_id: str) -> None:
        """
        Delete all rows for period_id.

        Called at the start of every generation run so that stale scores from
        a previous run are never mixed with the current results.
        """
        self._conn.execute("DELETE FROM scores WHERE period_id = ?", (period_id,))
        self._conn.commit()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._conn.close()

    def __enter__(self) -> "ScoresDatabase":
        return self

    def __exit__(self, *_) -> None:
        self.close()
