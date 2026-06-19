"""
ranking_query_engine.py
-----------------------
Read-only query interface for scores.db.

fetch_window() returns list[tuple] with columns in this fixed order:
    (batch_number, index_in_batch, min_days_required, avg_days_all,
     elective_conflicts, span_required, max_exams_per_day)
"""

import sqlite3
from pathlib import Path
from typing import Optional

VALID_METRIC_COLUMNS: frozenset = frozenset({
    "min_days_required", "avg_days_all", "elective_conflicts",
    "span_required", "max_exams_per_day",
})

ASCENDING_COLS: frozenset = frozenset({
    "elective_conflicts", "max_exams_per_day",
})

ROW_COLUMNS: tuple = (
    "batch_number", "index_in_batch",
    "min_days_required", "avg_days_all",
    "elective_conflicts", "span_required", "max_exams_per_day",
)


class RankingQueryEngine:
    """Read-only ranked retrieval from scores.db."""

    def __init__(self, db_path: Path) -> None:
        uri = db_path.as_uri() + "?mode=ro"
        self._conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def fetch_window(self, period_id: str, sort_cols: list,
                     limit: int, offset: int) -> list:
        """Return up to limit schedule references ranked by sort_cols."""
        order_clause = self._build_order_clause(sort_cols)
        rows = self._conn.execute(
            f"SELECT batch_number, index_in_batch, min_days_required, avg_days_all, "
            f"elective_conflicts, span_required, max_exams_per_day "
            f"FROM scores WHERE period_id = ? "
            f"ORDER BY {order_clause} LIMIT ? OFFSET ?",
            (period_id, limit, offset),
        ).fetchall()
        return [tuple(row) for row in rows]

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
