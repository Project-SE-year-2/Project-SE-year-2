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
        # Writes a batch of schedules for a specific period ID, appending to existing data if necessary
        if not schedules:
            self.update_manifest(period_id, 0)
            return

        # Load metadata to determine current progress
        manifest = self._load_manifest()
        existing_count = manifest.get(period_id, 0)
        
        # Calculate starting batch index based on existing count
        batch_index = existing_count // BATCH_SIZE
        written = 0
        
        # Iterate through the schedules list and split into chunks of BATCH_SIZE
        while written < len(schedules):
            batch = schedules[written : written + BATCH_SIZE]
            batch_file = self._batch_path(period_id, batch_index)
            
            # Check if file exists to prevent overwriting previous data
            if batch_file.exists():
                batch_index += 1
                continue

            # Ensure the directory exists and serialize the batch
            batch_file.parent.mkdir(parents=True, exist_ok=True)
            with open(batch_file, "wb") as f:
                pickle.dump(batch, f)

            # Update counters and persist manifest after every successfully written batch
            written += len(batch)
            existing_count += len(batch)
            batch_index += 1
            self.update_manifest(period_id, existing_count)

    # Updates the manifest with the new count of schedules for the given period ID
    def update_manifest(self, period_id: str, count: int) -> None:
        manifest = self._load_manifest()
        manifest[period_id] = count
        self._save_manifest(manifest)

    # Generate formatted filename: batch_0000.pkl, batch_0001.pkl, etc
    def _batch_path(self, period_id: str, batch_index: int) -> Path:
        
        return self._root / period_id / f"batch_{batch_index:04d}.pkl"

    # Manifest handling methods for reading and writing the index file that tracks result counts
    def _manifest_path(self) -> Path:
        return self._root / "manifest.json"

    # Loads the manifest file; returns an empty dict if it doesn't exist or is corrupted
    def _load_manifest(self) -> dict:
        manifest_path = self._manifest_path()
        if not manifest_path.exists():
            return {}
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    # Saves the manifest to disk, ensuring that the directory structure exists
    def _save_manifest(self, manifest: dict) -> None:
        # Atomic-like write of the manifest JSON file
        self._root.mkdir(parents=True, exist_ok=True)
        with open(self._manifest_path(), "w", encoding="utf-8") as f:
            json.dump(manifest, f)