import os
import tempfile
from src.app_controller import AppController


def _write(file_path: str, content: str):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def test_app_controller_end_to_end_creates_output(tmp_path):
    # Create a temporary project-like layout: tmp/data/*.txt
    project_root = tmp_path
    data_dir = project_root / "data"
    data_dir.mkdir()

    courses = """$$$$
Single Course
90001
Dr Tester
83101,1,FALL,Obligatory
Exam
"""
    dates = """$$$$
FALL, Aleph
01-01-2026, 01-01-2026
"""
    programs = """83101
"""

    courses_path = str(data_dir / "courses.txt")
    dates_path = str(data_dir / "dates.txt")
    programs_path = str(data_dir / "programs.txt")

    _write(courses_path, courses)
    _write(dates_path, dates)
    _write(programs_path, programs)

    controller = AppController()

    # Run the controller which will write into project_root/output
    controller.run(courses_path, dates_path, programs_path)

    output_dir = project_root / "output"

    # Ensure output directory exists and contains the schedule report
    assert output_dir.exists()

    files = list(output_dir.iterdir())
    assert any(p.name.startswith("schedule_output_") for p in files)

    # Basic content check
    report_file = files[0]
    content = report_file.read_text(encoding="utf-8")
    assert "TOTAL COMPLETE SCHEDULES" in content
    assert "1" in content
