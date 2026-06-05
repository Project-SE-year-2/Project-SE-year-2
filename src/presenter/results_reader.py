import json
import pickle
from pathlib import Path

from src.algorithm.period_results_writer import BATCH_SIZE
from src.models.exam_schedule import ExamSchedule


class ResultsReader:
    """
    Provides efficient read-only access to exam schedules stored in batched files.
    
    This class allows fetching specific schedules by index without loading an entire 
    period's results into RAM, relying on the batching structure created by PeriodResultsWriter.
    """

    def __init__(self, root_path: str | Path | None = None):
        # Set base directory for data storage
        self._root = Path(root_path) if root_path else Path(__file__).parents[2] / "data" / "results"

    # Returns the total number of schedules stored for a specific period
    def get_count(self, period_id: str) -> int:
        manifest = self._load_manifest()
        return int(manifest.get(period_id, 0))

    # Retrieves a single schedule by its global index across all batches for the specified period
    def get_schedule_at(self, period_id: str, index: int) -> ExamSchedule:
        # Validates index bounds
        if index < 0:
            raise IndexError("Schedule index cannot be negative.")

        count = self.get_count(period_id)
        if index >= count:
            raise IndexError(f"Schedule index {index} is out of range for period '{period_id}'.")

        # Calculate which batch file holds the requested index
        batch_num = index // BATCH_SIZE
        batch_path = self._batch_path(period_id, batch_num)
        
        if not batch_path.exists():
            raise FileNotFoundError(f"Batch file not found: {batch_path}")

        # Load only the required batch into memory
        with open(batch_path, "rb") as f:
            batch = pickle.load(f)

        # Retrieve the specific item using modulo (remainder) operator
        return batch[index % BATCH_SIZE]
    
    # Generate formatted filename: batch_0000.pkl, batch_0001.pkl, etc.
    def _batch_path(self, period_id: str, batch_index: int) -> Path:    
        return self._root / period_id / f"batch_{batch_index:04d}.pkl"

    # Returns the path to the manifest file that tracks total schedule counts per period
    def _manifest_path(self) -> Path:
        return self._root / "manifest.json"

    # Returns all period identifiers found in the manifest
    def get_period_ids(self) -> list[str]:
        manifest = self._load_manifest()
        return list(manifest.keys())

     # Reads the central index file; fails gracefully if missing
    def _load_manifest(self) -> dict:
        manifest_path = self._manifest_path()
        if not manifest_path.exists():
            return {}
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}