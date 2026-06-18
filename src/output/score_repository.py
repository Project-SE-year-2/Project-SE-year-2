import sqlite3
from pathlib import Path

from src.models.schedule_score import ScheduleScore


# Default location of the scores database inside the project data folder
_DEFAULT_DB = Path(__file__).parents[2] / "data" / "scores.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS scores (
    run_id       TEXT    NOT NULL,
    schedule_idx INTEGER NOT NULL,
    avg_gap      REAL    NOT NULL,
    min_gap      INTEGER NOT NULL,
    spread       INTEGER NOT NULL,
    collisions   INTEGER NOT NULL,
    max_per_day  INTEGER NOT NULL,
    PRIMARY KEY (run_id, schedule_idx)
)
"""


class ScoreRepository:
    """
    Persists ScheduleScore objects to a local SQLite database (scores.db).
    Each generation run is identified by a run_id (e.g. a timestamp string).
    Scores can be reloaded later for re-ranking without re-running the engine.
    """

    def __init__(self, db_path: Path | str | None = None):
        self._path = Path(db_path) if db_path else _DEFAULT_DB
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Create the scores table if it does not already exist."""
        with self._connect() as conn:
            conn.execute(_CREATE_TABLE)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def save(self, run_id: str, schedule_idx: int, score: ScheduleScore) -> None:
        """Persist one score entry. Replaces any existing entry for the same key."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO scores
                    (run_id, schedule_idx, avg_gap, min_gap, spread, collisions, max_per_day)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, schedule_idx, score.avg_gap, score.min_gap,
                 score.spread, score.collisions, score.max_per_day),
            )

    def save_all(self, run_id: str, scored: list[tuple[int, ScheduleScore]]) -> None:
        """Persist multiple scores for a run in a single transaction."""
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO scores
                    (run_id, schedule_idx, avg_gap, min_gap, spread, collisions, max_per_day)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (run_id, idx, s.avg_gap, s.min_gap, s.spread, s.collisions, s.max_per_day)
                    for idx, s in scored
                ],
            )

    def load(self, run_id: str) -> list[tuple[int, ScheduleScore]]:
        """Return all scores for a run ordered by schedule_idx."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT schedule_idx, avg_gap, min_gap, spread, collisions, max_per_day
                FROM scores
                WHERE run_id = ?
                ORDER BY schedule_idx
                """,
                (run_id,),
            ).fetchall()

        return [
            (row[0], ScheduleScore(avg_gap=row[1], min_gap=row[2],
                                   spread=row[3], collisions=row[4], max_per_day=row[5]))
            for row in rows
        ]

    def list_runs(self) -> list[str]:
        """Return all distinct run_ids stored in the database."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT run_id FROM scores ORDER BY run_id"
            ).fetchall()
        return [row[0] for row in rows]

    def delete_run(self, run_id: str) -> None:
        """Remove all scores for a specific run."""
        with self._connect() as conn:
            conn.execute("DELETE FROM scores WHERE run_id = ?", (run_id,))

    def clear(self) -> None:
        """Wipe all stored scores."""
        with self._connect() as conn:
            conn.execute("DELETE FROM scores")
