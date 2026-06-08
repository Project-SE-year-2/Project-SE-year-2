from datetime import date

from PyQt5.QtCore import QDate

from src.views.widgets.period_editor_widget import PeriodEditorWidget


class MockAppService:
    # Creates a small fake service used by the tests instead of the real application service.
    def __init__(self):
        self.periods = [
            {
                "id": "FALL_Aleph",
                "semester": "FALL",
                "moed": "Aleph",
                "start_date": date(2026, 1, 29),
                "end_date": date(2026, 3, 11),
                "allowed_days": [],
                "forbidden_days": [date(2026, 2, 3)],
            },
            {
                "id": "SPRI_Aleph",
                "semester": "SPRI",
                "moed": "Aleph",
                "start_date": date(2026, 7, 3),
                "end_date": date(2026, 8, 7),
                "allowed_days": [],
                "forbidden_days": [],
            },
        ]
        self.toggled_days = []
        self.shift_calls = []

    # Returns the fake period list expected by PeriodEditorWidget.
    def get_periods(self):
        return self.periods

    # Records every toggled day so tests can verify the editor behavior.
    def toggle_day(self, period_id, day):
        self.toggled_days.append((period_id, day))

    # Records every period range update and validates that start is before end.
    def shift_period(self, period_id, start, end):
        if start >= end:
            raise ValueError("Start date must be before end date.")
        self.shift_calls.append((period_id, start, end))


# Tests that loading a period stores the current period id.
def test_period_editor_load_period_sets_current_period(qtbot):
    service = MockAppService()
    widget = PeriodEditorWidget(service)

    qtbot.addWidget(widget)
    widget.load_period("FALL_Aleph")

    assert widget.current_period_id() == "FALL_Aleph"


# Tests that loading a period updates the title text with the selected period details.
def test_period_editor_load_period_updates_title(qtbot):
    service = MockAppService()
    widget = PeriodEditorWidget(service)

    qtbot.addWidget(widget)
    widget.load_period("FALL_Aleph")

    assert "FALL" in widget._title_label.text()
    assert "Aleph" in widget._title_label.text()


# Tests that clicking a calendar day calls toggle_day on the service.
def test_period_editor_day_click_toggles_day(qtbot):
    service = MockAppService()
    widget = PeriodEditorWidget(service)

    qtbot.addWidget(widget)
    widget.load_period("FALL_Aleph")
    widget._on_day_clicked(QDate(2026, 2, 10))

    assert service.toggled_days == [("FALL_Aleph", date(2026, 2, 10))]


# Tests that saving a valid date range calls shift_period on the service.
def test_period_editor_save_calls_shift_period(qtbot):
    service = MockAppService()
    widget = PeriodEditorWidget(service)

    qtbot.addWidget(widget)
    widget.load_period("FALL_Aleph")

    widget._on_save_requested(
        QDate(2026, 1, 30),
        QDate(2026, 3, 12),
        {QDate(2026, 2, 3)},
    )

    assert service.shift_calls[0] == (
        "FALL_Aleph",
        date(2026, 1, 30),
        date(2026, 3, 12),
    )


# Tests that saving does not re-toggle forbidden days that were already handled by day clicks.
def test_period_editor_save_does_not_toggle_days_again(qtbot):
    service = MockAppService()
    widget = PeriodEditorWidget(service)

    qtbot.addWidget(widget)
    widget.load_period("FALL_Aleph")

    widget._on_save_requested(
        QDate(2026, 1, 29),
        QDate(2026, 3, 11),
        {QDate(2026, 2, 4)},
    )

    assert service.toggled_days == []


# Tests that invalid date ranges show an error message instead of crashing.
def test_period_editor_invalid_date_range_shows_error(qtbot):
    service = MockAppService()
    widget = PeriodEditorWidget(service)

    qtbot.addWidget(widget)
    widget.load_period("FALL_Aleph")

    widget._on_save_requested(
        QDate(2026, 3, 11),
        QDate(2026, 1, 29),
        set(),
    )

    assert "Error:" in widget._status_label.text()


# Tests that clear resets the selected period state.
def test_period_editor_clear_resets_current_period(qtbot):
    service = MockAppService()
    widget = PeriodEditorWidget(service)

    qtbot.addWidget(widget)
    widget.load_period("FALL_Aleph")
    widget.clear()

    assert widget.current_period_id() is None
