from datetime import date
from src.exam_period_file_parser import ExamPeriodFileParser

# A test to check that the system put the forbidden day in the list of forbidden days
def test_parse_forbidden_dates_single_dates():
    lines = [
        "FALL, Aleph",
        "29-01-2026, 11-03-2026",
        "- 31-01-2026 Shabat",
        "- 07-02-2026",
    ]

    parser = ExamPeriodFileParser()
    forbidden = parser._parse_forbidden_dates(
        lines,
        date(2026, 1, 29),
        date(2026, 3, 11),
    )

    assert date(2026, 1, 31) in forbidden
    assert date(2026, 2, 7) in forbidden
    assert len(forbidden) == 2

# A test that checks that the system can handle multuple consecutive forbidden days
def test_parse_forbidden_dates_range():
    lines = [
        "FALL, Aleph",
        "29-01-2026, 11-03-2026",
        "- 02-03-2026, 04-03-2026 Purim",
    ]

    parser = ExamPeriodFileParser()
    forbidden = parser._parse_forbidden_dates(
        lines,
        date(2026, 1, 29),
        date(2026, 3, 11),
    )

    assert date(2026, 3, 2) in forbidden
    assert date(2026, 3, 3) in forbidden
    assert date(2026, 3, 4) in forbidden

    assert len(forbidden) == 3

# A test that checks that the system ignores dates that not included in our Dates file
def test_parse_forbidden_dates_outside_period_are_ignored():
    lines = [
        "FALL, Aleph",
        "29-01-2026, 11-03-2026",
        "- 01-01-2026 Outside period",
        "- 20-03-2026 Outside period",
    ]

    parser = ExamPeriodFileParser()
    forbidden = parser._parse_forbidden_dates(
        lines,
        date(2026, 1, 29),
        date(2026, 3, 11),
    )

    assert forbidden == set()