from datetime import date
from src.exam_period_file_parser import ExamPeriodFileParser

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

    assert period.semester == "FALL"
    assert period.moed == "Aleph"

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

    assert periods[0].semester == "FALL"
    assert periods[0].moed == "Aleph"

    assert periods[1].semester == "SPRI"
    assert periods[1].moed == "Bet"