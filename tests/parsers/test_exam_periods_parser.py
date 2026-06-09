from datetime import date
from src.parsers.exam_period_file_parser import ExamPeriodFileParser
from src.models.enums import Semester, Moed

# A test that checks that the systems filters the forbidden dates and do not put them in possible_dates
def test_parse_exam_periods_file_creates_possible_dates_without_forbidden_dates(tmp_path):
    content = """$$$$
FALL, Aleph
29-01-2026, 03-02-2026
- 31-01-2026 Shabat
- 02-02-2026, 03-02-2026 Holiday
"""

    file_path = tmp_path / "dates.txt"
    file_path.write_text(content, encoding="utf-8")

    # Instantiate the class and call the parse method
    parser = ExamPeriodFileParser()
    periods = parser.parse(str(file_path))

    assert len(periods) == 1

    period = periods[0]

    assert period.semester == Semester.FALL
    assert period.moed == Moed.Aleph

    assert period.start_date == date(2026, 1, 29)
    assert period.end_date == date(2026, 2, 3)

    assert date(2026, 1, 29) in period.possible_dates
    assert date(2026, 1, 30) in period.possible_dates

    assert date(2026, 1, 31) not in period.possible_dates
    assert date(2026, 2, 2) not in period.possible_dates
    assert date(2026, 2, 3) not in period.possible_dates

# A test that checks that our system can support multiple exam periods 
def test_parse_exam_periods_file_loads_multiple_periods(tmp_path):
    content = """$$$$
FALL, Aleph
29-01-2026, 30-01-2026
$$$$
SPRI, Bet
10-07-2026, 11-07-2026
"""

    file_path = tmp_path / "dates.txt"
    file_path.write_text(content, encoding="utf-8")

    parser = ExamPeriodFileParser()
    periods = parser.parse(str(file_path))

    assert len(periods) == 2

    assert periods[0].semester == Semester.FALL
    assert periods[0].moed == Moed.Aleph

    assert periods[1].semester == Semester.SPRI
    assert periods[1].moed == Moed.Bet


def test_parse_exam_period_forbidden_range_clamped_to_period(tmp_path):
    """A forbidden date range that extends beyond the period boundaries is clamped."""
    content = """$$$$
FALL, Aleph
03-01-2026, 07-01-2026
- 01-01-2026, 05-01-2026 Holiday
"""
    file_path = tmp_path / "dates.txt"
    file_path.write_text(content, encoding="utf-8")

    parser = ExamPeriodFileParser()
    periods = parser.parse(str(file_path))

    period = periods[0]
    # Only days within [3 Jan, 7 Jan] should be affected
    assert date(2026, 1, 3) not in period.possible_dates
    assert date(2026, 1, 4) not in period.possible_dates
    assert date(2026, 1, 5) not in period.possible_dates
    # Days outside the forbidden range but inside the period should remain
    assert date(2026, 1, 6) in period.possible_dates
    assert date(2026, 1, 7) in period.possible_dates


def test_parse_exam_period_all_days_forbidden(tmp_path):
    """When all days in the period are forbidden, possible_dates should be empty."""
    content = """$$$$
FALL, Aleph
01-01-2026, 02-01-2026
- 01-01-2026, 02-01-2026 Holiday
"""
    file_path = tmp_path / "dates.txt"
    file_path.write_text(content, encoding="utf-8")

    parser = ExamPeriodFileParser()
    periods = parser.parse(str(file_path))

    assert len(periods[0].possible_dates) == 0


def test_parse_exam_period_no_forbidden_lines(tmp_path):
    """A period with no forbidden date lines keeps all dates as possible."""
    content = """$$$$
SPRI, Bet
10-06-2026, 14-06-2026
"""
    file_path = tmp_path / "dates.txt"
    file_path.write_text(content, encoding="utf-8")

    parser = ExamPeriodFileParser()
    periods = parser.parse(str(file_path))

    assert len(periods) == 1
    assert len(periods[0].possible_dates) == 5


def test_parse_exam_period_empty_file(tmp_path):
    """An empty exam periods file returns an empty list."""
    file_path = tmp_path / "dates.txt"
    file_path.write_text("", encoding="utf-8")

    parser = ExamPeriodFileParser()
    periods = parser.parse(str(file_path))

    assert periods == []

