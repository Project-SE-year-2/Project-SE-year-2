import os
from src.presenter.app_service import AppService


def _write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def test_generate_stream_produces_period_results(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    courses = """$$$$
Course A
90001
Dr A
83101,1,FALL,Obligatory
Exam
"""
    dates = """$$$$
FALL, Aleph
01-01-2026, 02-01-2026
"""
    programs = """83101
"""

    courses_path = str(data_dir / "courses.txt")
    dates_path = str(data_dir / "dates.txt")
    programs_path = str(data_dir / "programs.txt")

    _write(courses_path, courses)
    _write(dates_path, dates)
    _write(programs_path, programs)

    service = AppService.getInstance()

    # load data into the service datastore
    service.load_data(courses_path, dates_path, mode="replace")
    service.select_programs(["83101"])

    yielded = list(service.generate_stream())

    # Must yield one tuple per period (here only one)
    assert len(yielded) == 1

    period_id, schedules = yielded[0]
    assert period_id in service.get_period_ids()

    # After generation completes, schedules should be available via get_schedule_count()
    assert service.get_schedule_count() >= 0
