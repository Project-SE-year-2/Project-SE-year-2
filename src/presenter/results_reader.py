import json
import pickle
from pathlib import Path

from src.algorithm.period_results_writer import BATCH_SIZE
from src.models.exam_schedule import ExamSchedule


class ResultsReader:
    """
    Provides efficient read-only access to exam schedules stored in batched files.

    Caches manifest files and batch files in memory so repeated reads during
    polling (every 150 ms) don't hit the disk each time.
    """

    def __init__(self, root_path: str | Path | None = None):
        self._root = Path(root_path) if root_path else Path(__file__).parents[2] / "data" / "results"
        # Cache: period_id -> {"count": int, "mtime": float}
        self._manifest_cache: dict[str, dict] = {}
        # Cache: (period_id, batch_num) -> (mtime: float, batch: list)
        self._batch_cache: dict[tuple, tuple] = {}

    def get_count(self, period_id: str) -> int:
        manifest = self._load_manifest(period_id)
        return int(manifest.get("count", 0))

    def get_schedule_at(self, period_id: str, index: int) -> ExamSchedule:
        if index < 0:
            raise IndexError("Schedule index cannot be negative.")

        count = self.get_count(period_id)
        if index >= count:
            raise IndexError(f"Schedule index {index} is out of range for period '{period_id}'.")

        batch_num = index // BATCH_SIZE
        batch_path = self._batch_path(period_id, batch_num)

        if not batch_path.exists():
            raise FileNotFoundError(f"Batch file not found: {batch_path}")

        batch = self._load_batch(period_id, batch_num, batch_path)
        return batch[index % BATCH_SIZE]

    def get_period_ids(self) -> list[str]:
        if not self._root.exists():
            return []
        return [p.name for p in self._root.iterdir() if p.is_dir() and (p / "manifest.json").exists()]

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _load_manifest(self, period_id: str) -> dict:
        manifest_path = self._root / period_id / "manifest.json"
        if not manifest_path.exists():
            self._manifest_cache.pop(period_id, None)
            return {}
        try:
            mtime = manifest_path.stat().st_mtime
            cached = self._manifest_cache.get(period_id)
            if cached and cached.get("_mtime") == mtime:
                return cached
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["_mtime"] = mtime
            self._manifest_cache[period_id] = data
            return data
        except Exception:
            return {}

    def _load_batch(self, period_id: str, batch_num: int, batch_path: Path) -> list:
        key = (period_id, batch_num)
        mtime = batch_path.stat().st_mtime
        cached = self._batch_cache.get(key)
        if cached and cached[0] == mtime:
            return cached[1]
        with open(batch_path, "rb") as f:
            batch = pickle.load(f)
        self._batch_cache[key] = (mtime, batch)
        return batch

    def _batch_path(self, period_id: str, batch_index: int) -> Path:
        return self._root / period_id / f"batch_{batch_index:04d}.pkl"
