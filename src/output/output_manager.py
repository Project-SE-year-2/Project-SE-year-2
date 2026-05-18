import os
from datetime import datetime
from src.output.i_output_writer import IOutputWriter
from src.models.exam_schedule import ExamSchedule
from src.models.exam_period import ExamPeriod


class OutputManager:
    """
    Manages the output pipeline.
    Responsible for:
    - Preparing the output directory.
    - Generating a unique timestamped filename per run.
    - Delegating the actual writing to all registered IOutputWriter implementations.
    """

    def __init__(self, writers: list[IOutputWriter]):
        self._writers = writers

    def prepareOutputDir(self, path: str) -> None:
        """Create the output directory if it does not already exist."""
        os.makedirs(path, exist_ok=True)

    def writeReport(
        self,
        schedules: list[ExamSchedule],
        metadata: dict[ExamPeriod, dict],
        programs: list[str],
        output_dir: str,
    ) -> None:
        """Generate a timestamped output path and delegate writing to all registered writers."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"schedule_output_{timestamp}.txt")
        for writer in self._writers:
            writer.write(schedules, metadata, programs, output_path)
