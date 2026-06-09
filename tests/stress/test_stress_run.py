import os
import sys
import subprocess
from pathlib import Path
import pytest


@pytest.mark.stress
@pytest.mark.skipif(os.environ.get("RUN_STRESS") != "1", reason="Stress test — set RUN_STRESS=1 to run")
def test_stress_run_cli_creates_output(tmp_path):
    """Runs the CLI with the large stress inputs and verifies an output file is produced.

    This test is intentionally long-running and skipped by default. To execute it
    locally set `RUN_STRESS=1` in your environment and run pytest with the
    `-m stress` marker, for example:

        RUN_STRESS=1 pytest -m stress tests/stress/test_stress_run.py -q

    """
    repo = Path(__file__).resolve().parents[2]
    data_dir = repo / "tests" / "stress test" / "data"

    courses = data_dir / "stress_courses.txt"
    dates = data_dir / "stress_dates.txt"
    programs = data_dir / "stress_programs.txt"

    assert courses.exists() and dates.exists() and programs.exists(), (
        f"Stress data files not found in {data_dir}"
    )

    # Run the CLI as a subprocess using the same Python executable
    script = repo / "src" / "cli_main.py"
    assert script.exists(), f"CLI entrypoint not found at {script}"

    # Create an isolated output directory inside tmp_path so we can assert on results
    out_dir = repo / "output"

    # Run the CLI (may take a long time depending on the stress data size)
    subprocess.run([sys.executable, str(script), str(courses), str(dates), str(programs)], cwd=str(repo), check=True)

    # Verify that an output file has been created
    files = list(out_dir.glob("schedule_output_*.txt"))
    assert files, "No schedule output file was created by the stress run"
