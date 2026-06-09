import json
import os
import pickle
from pathlib import Path

from src.models.exam_schedule import ExamSchedule

# Defines the number of schedules per file to keep memory usage low
BATCH_SIZE = 50


class PeriodResultsWriter:
    """
    Handles the persistence of exam schedule results by partitioning data into batches.
    
    This class implements a pagination strategy for results:
    - Writes schedules to disk in chunks (batches) to avoid loading entire periods into RAM.
    - Maintains a 'manifest.json' index to track total results per period ID.
    - Ensures data integrity by never overwriting existing batch files.
    """
    
    def __init__(self, root_path: str | Path | None = None):
        # Set base directory for data storage
        self._root = Path(root_path) if root_path else Path(__file__).parents[2] / "data" / "results"
        self._root.mkdir(parents=True, exist_ok=True)

    def write_batch(self, period_id: str, schedules: list[ExamSchedule]) -> None:
        if not schedules:
            self.update_manifest(period_id, 0)
            return

        manifest = self._load_manifest(period_id)
        existing_count = manifest.get("count", 0)
        
        batch_index = existing_count // BATCH_SIZE
        remainder = existing_count % BATCH_SIZE
        
        written = 0
        
        # If the last batch is not completely full, append to it first
        if remainder > 0:
            batch_file = self._batch_path(period_id, batch_index)
            partial_batch = []
            if batch_file.exists():
                with open(batch_file, "rb") as f:
                    partial_batch = pickle.load(f)
                    
            space_left = BATCH_SIZE - remainder
            to_add = schedules[:space_left]
            partial_batch.extend(to_add)
            
            batch_file.parent.mkdir(parents=True, exist_ok=True)
            temp_batch_file = batch_file.with_suffix(".tmp")
            with open(temp_batch_file, "wb") as f:
                pickle.dump(partial_batch, f)
            temp_batch_file.replace(batch_file)
            
            written += len(to_add)
            existing_count += len(to_add)
            self.update_manifest(period_id, existing_count)
            batch_index += 1

        # Now write the rest in perfect chunks of BATCH_SIZE
        while written < len(schedules):
            batch = schedules[written : written + BATCH_SIZE]
            batch_file = self._batch_path(period_id, batch_index)
            
            batch_file.parent.mkdir(parents=True, exist_ok=True)
            temp_batch_file = batch_file.with_suffix(".tmp")
            with open(temp_batch_file, "wb") as f:
                pickle.dump(batch, f)
            temp_batch_file.replace(batch_file)

            written += len(batch)
            existing_count += len(batch)
            self.update_manifest(period_id, existing_count)
            batch_index += 1

    # Updates the manifest with the new count of schedules for the given period ID
    def update_manifest(self, period_id: str, count: int) -> None:
        manifest_path = self._root / period_id / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = manifest_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump({"count": count}, f)
        temp_path.replace(manifest_path)

    # Generate formatted filename: batch_0000.pkl, batch_0001.pkl, etc
    def _batch_path(self, period_id: str, batch_index: int) -> Path:
        
        return self._root / period_id / f"batch_{batch_index:04d}.pkl"

    # Loads the manifest file; returns an empty dict if it doesn't exist or is corrupted
    def _load_manifest(self, period_id: str) -> dict:
        manifest_path = self._root / period_id / "manifest.json"
        if not manifest_path.exists():
            return {}
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def clear_period(self, period_id: str) -> None:
        """Delete all batch files for a period and reset its manifest count to 0.

        Called at the start of every generate run so that stale results from a
        previous run never mix with the current one.
        """
        import shutil
        period_dir = self._root / period_id
        
        # Instantly set manifest to 0 so readers stop looking for batch files
        self.update_manifest(period_id, 0)
        
        # Then clean up old batch files rapidly using rmtree
        if period_dir.exists():
            shutil.rmtree(period_dir, ignore_errors=True)
            
        period_dir.mkdir(parents=True, exist_ok=True)
        self.update_manifest(period_id, 0)
