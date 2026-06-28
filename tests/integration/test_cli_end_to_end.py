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


def test_app_controller_ranking_order(tmp_path):
    project_root = tmp_path
    data_dir = project_root / "data"
    data_dir.mkdir()

    courses = """$$$$
Course 1
C1
Dr Tester
83101,1,FALL,Obligatory
Exam
$$$$
Course 2
C2
Dr Tester
83101,1,FALL,Obligatory
Exam
"""
    dates = """$$$$
FALL, Aleph
01-01-2026, 03-01-2026
"""
    programs = """83101
"""

    courses_path = str(data_dir / "courses.txt")
    dates_path = str(data_dir / "dates.txt")
    programs_path = str(data_dir / "programs.txt")

    _write(courses_path, courses)
    _write(dates_path, dates)
    _write(programs_path, programs)

    from src.app_controller import AppController
    controller = AppController()
    
    # Run the controller with ranking config targeting avg_days_all.
    # The solver will generate schedules with varying gaps.
    # We expect the one with the maximum gap (Jan 1 and Jan 3 -> 2 days) to be ranked first.
    controller.run(courses_path, dates_path, programs_path, ranking_config=["avg_days_all"])

    output_dir = project_root / "output"
    assert output_dir.exists()
    
    files = list(output_dir.iterdir())
    assert any(p.name.startswith("schedule_output_") for p in files)

    report_file = files[0]
    content = report_file.read_text(encoding="utf-8")
    
    lines = content.splitlines()
    
    # Find the lines for C1 and C2 in the FIRST schedule output.
    first_schedule_lines = []
    in_first_schedule = False
    for line in lines:
        if "Schedule #2" in line:
            break
        first_schedule_lines.append(line)
        
    dates_found = set()
    for line in first_schedule_lines:
        if "(C1)" in line or "(C2)" in line:
            if "01-01-2026" in line:
                dates_found.add("01-01-2026")
            if "02-01-2026" in line:
                dates_found.add("02-01-2026")
            if "03-01-2026" in line:
                dates_found.add("03-01-2026")
                
    assert "01-01-2026" in dates_found
    assert "03-01-2026" in dates_found
    assert "02-01-2026" not in dates_found, "The top schedule should not contain the middle date because avg_days_all maximizes the gap."
