import sqlite3
from pathlib import Path

from src.models.schedule_score import ScheduleMetrics


# Default location — full schema refactor tracked under EP-116 (ScoresDatabase).
_DEFAULT_DB = Path(__file__).parents[2] / "data" / "scores.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS scores (
    run_id            TEXT    NOT NULL,
    schedule_idx      INTEGER NOT NULL,
    avg_days_all      REAL    NOT NULL,
    min_days_required INTEGER NOT NULL,
    span_required     INTEGER NOT NULL,
    elective_conflicts INTEGER NOT NULL,
    max_exams_per_day INTEGER NOT NULL,
    PRIMARY KEY (run_id, schedule_idx)
)
"""


class ScoreRepository:
    """
    Temporary persistence layer for ScheduleMetrics.
    Full schema (period_id, batch_number, index_in_batch, …) is tracked under EP-116.
    """

    def __init__(self, db_path: Path | str | None = None):
        self._path = Path(db_path) if db_path else _DEFAULT_DB
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(_CREATE_TABLE)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def save(self, run_id: str, schedule_idx: int, score: ScheduleMetrics) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO scores
                    (run_id, schedule_idx, avg_days_all, min_days_required,
                     span_required, elective_conflicts, max_exams_per_day)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, schedule_idx, score.avg_days_all, score.min_days_required,
                 score.span_required, score.elective_conflicts, score.max_exams_per_day),
            )

    def save_all(self, run_id: str, scored: list[tuple[int, ScheduleMetrics]]) -> None:
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO scores
                    (run_id, schedule_idx, avg_days_all, min_days_required,
                     span_required, elective_conflicts, max_exams_per_day)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (run_id, idx, s.avg_days_all, s.min_days_required,
                     s.span_required, s.elective_conflicts, s.max_exams_per_day)
                    for idx, s in scored
                ],
            )

    def load(self, run_id: str) -> list[tuple[int, ScheduleMetrics]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT schedule_idx, avg_days_all, min_days_required,
                       span_required, elective_conflicts, max_exams_per_day
                FROM scores WHERE run_id = ? ORDER BY schedule_idx
                """,
                (run_id,),
            ).fetchall()
        return [
            (row[0], ScheduleMetrics(
                avg_days_all=row[1], min_days_required=row[2],
                span_required=row[3], elective_conflicts=row[4], max_exams_per_day=row[5],
            ))
            for row in rows
        ]

    def list_runs(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT run_id FROM scores ORDER BY run_id"
            ).fetchall()
        return [row[0] for row in rows]

    def delete_run(self, run_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM scores WHERE run_id = ?", (run_id,))

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM scores")
