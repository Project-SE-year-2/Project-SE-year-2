import pytest
from src.parsers.exam_period_file_parser import ExamPeriodFileParser


def test_parse_exam_periods_invalid_date_format_raises(tmp_path):
    # start date in wrong format should raise ValueError during parsing
    content = """$$$$
FALL, Aleph
2026-01-01, 05-01-2026
"""
    file_path = tmp_path / "dates.txt"
    file_path.write_text(content, encoding="utf-8")

    parser = ExamPeriodFileParser()
    with pytest.raises(ValueError):
        parser.parse(str(file_path))


def test_forbidden_dates_outside_period_ignored(tmp_path):
    # Forbidden dates outside the period should be ignored
    content = """$$$$
FALL, Aleph
01-01-2026, 02-01-2026
- 05-01-2026 Holiday
- 31-12-2025 Holiday
"""
    file_path = tmp_path / "dates.txt"
    file_path.write_text(content, encoding="utf-8")

    parser = ExamPeriodFileParser()
    periods = parser.parse(str(file_path))
    assert len(periods) == 1
    period = periods[0]
    # Only the two days in range should be possible
    assert len(period.possible_dates) == 2
    # Ensure forbidden_days only contains dates inside the period (none)
    assert all(d >= period.start_date and d <= period.end_date for d in period.forbidden_days)
