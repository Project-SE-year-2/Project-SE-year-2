"""
ranking_query_engine.py
-----------------------
Query interface for ranked schedule retrieval from scores.db.

fetch_window() returns list[tuple] with columns in this fixed order:
    (batch_number, index_in_batch, min_days_required, avg_days_all,
     elective_conflicts, span_required, max_exams_per_day, avg_room_distance)

Dynamic index strategy
----------------------
ScoresDatabase pre-creates one composite index per single metric column
(period_id, col).  When the caller sorts by two or more columns SQLite can
only use the first-column index and must sort the rest in memory — O(N log N)
on millions of rows.

_ensure_index_for() closes this gap: the first time a particular sort_cols
combination is seen it issues CREATE INDEX IF NOT EXISTS for the full
multi-column composite (including tie-breaker columns batch_number and
index_in_batch), then caches the combination in _built_indexes so that
subsequent calls skip the DB round-trip entirely.  This guarantees SQLite
uses a COVERING INDEX for the full ORDER BY with no TEMP B-TREE fallback.
"""

import sqlite3
from pathlib import Path
from typing import Optional

VALID_METRIC_COLUMNS: frozenset = frozenset({
    "min_days_required", "avg_days_all", "elective_conflicts",
    "span_required", "max_exams_per_day", "avg_room_distance",
})

ASCENDING_COLS: frozenset = frozenset({
    "elective_conflicts", "max_exams_per_day", "avg_room_distance",
})

ROW_COLUMNS: tuple = (
    "batch_number", "index_in_batch",
    "min_days_required", "avg_days_all",
    "elective_conflicts", "span_required", "max_exams_per_day",
    "avg_room_distance",
)


class RankingQueryEngine:
    """Ranked retrieval from scores.db with on-demand composite index creation."""

    def __init__(self, db_path: Path) -> None:
        # Read-write connection required so _ensure_index_for() can CREATE INDEX.
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.row_factory = sqlite3.Row
        # In-memory cache of sort_cols tuples for which a composite index already
        # exists.  Avoids a DB round-trip on every fetch_window() call.
        self._built_indexes: set[tuple] = set()

    # ------------------------------------------------------------------
    # Dynamic composite index
    # ------------------------------------------------------------------

    def _ensure_index_for(self, sort_cols: list) -> None:
        """Create a composite index for sort_cols if one does not exist yet.

        Single-column combinations are already covered by the static indexes
        in ScoresDatabase, so we skip them to avoid duplicate index names that
        could confuse the query planner.
        """
        key = tuple(sort_cols)

        # Fast path: already created this session — no DB round-trip needed.
        if key in self._built_indexes:
            return

        # Single-column: static index from ScoresDatabase already covers this.
        if len(sort_cols) == 1:
            self._built_indexes.add(key)
            return

        # Build a stable, SQL-safe index name from the column list.
        cols_signature = "_".join(sort_cols)
        idx_name = f"idx_dynamic_{cols_signature}"

        # Include the tie-breaker columns so SQLite can satisfy the full
        # ORDER BY (col1, col2, ..., batch_number ASC, index_in_batch ASC)
        # from the index alone, eliminating the TEMP B-TREE step.
        order_clause = self._build_order_clause(sort_cols)

        self._conn.execute(
            f"CREATE INDEX IF NOT EXISTS {idx_name} "
            f"ON scores (period_id, {order_clause}, batch_number ASC, index_in_batch ASC)"
        )
        self._conn.commit()

        # Cache so future calls with the same combination skip the DB round-trip.
        self._built_indexes.add(key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_window(self, period_id: str, sort_cols: list,
                     limit: int, offset: int) -> list:
        """Return up to limit schedule references ranked by sort_cols.

        Ensures a composite index exists for the requested sort combination
        before executing the query so that multi-column ORDER BY never falls
        back to a full-table sort.
        """
        if limit <= 0:
            raise ValueError(f"limit must be a positive integer, got {limit}")
        if offset < 0:
            raise ValueError(f"offset must be non-negative, got {offset}")

        order_clause = self._build_order_clause(sort_cols)

        # Guarantee an index covering (period_id, col1, col2, ...) exists.
        self._ensure_index_for(sort_cols)

        # Tie-breaker ensures deterministic ordering and stable pagination
        # when multiple rows share identical metric values.
        rows = self._conn.execute(
            f"SELECT batch_number, index_in_batch, min_days_required, avg_days_all, "
            f"elective_conflicts, span_required, max_exams_per_day, avg_room_distance "
            f"FROM scores WHERE period_id = ? "
            f"ORDER BY {order_clause}, batch_number ASC, index_in_batch ASC "
            f"LIMIT ? OFFSET ?",
            (period_id, limit, offset),
        ).fetchall()
        return rows

    def best_score(self, period_id: str, primary_col: str) -> Optional[float]:
        """Return the best (rank-1) value of primary_col for this period."""
        if primary_col not in VALID_METRIC_COLUMNS:
            raise ValueError(
                f"Unknown metric column: {primary_col!r}. "
                f"Valid columns: {sorted(VALID_METRIC_COLUMNS)}"
            )
        direction = "ASC" if primary_col in ASCENDING_COLS else "DESC"
        row = self._conn.execute(
            f"SELECT {primary_col} FROM scores WHERE period_id = ? "
            f"ORDER BY {primary_col} {direction} LIMIT 1",
            (period_id,),
        ).fetchone()
        return row[0] if row is not None else None

    def count(self, period_id: str) -> int:
        """Return the total number of scored schedules for this period."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM scores WHERE period_id = ?", (period_id,)
        ).fetchone()
        return row[0] if row else 0

    def _build_order_clause(self, sort_cols: list) -> str:
        """Validate sort_cols and build ORDER BY clause."""
        if not sort_cols:
            raise ValueError(
                f"sort_cols must contain at least one column. "
                f"Valid options: {sorted(VALID_METRIC_COLUMNS)}"
            )
        terms = []
        for col in sort_cols:
            if col not in VALID_METRIC_COLUMNS:
                raise ValueError(
                    f"Unknown sort column: {col!r}. "
                    f"Valid columns: {sorted(VALID_METRIC_COLUMNS)}"
                )
            direction = "ASC" if col in ASCENDING_COLS else "DESC"
            terms.append(f"{col} {direction}")
        return ", ".join(terms)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
