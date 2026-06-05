from datetime import date

from src.views.widgets.period_list_widget import PeriodListWidget


class MockAppService:
    def __init__(self):
        self.periods = [
            {
                "id": "FALL_Aleph",
                "semester": "FALL",
                "moed": "Aleph",
                "start_date": date(2026, 1, 29),
                "end_date": date(2026, 3, 11),
                "allowed_days": [],
                "forbidden_days": [],
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

    def get_periods(self):
        return self.periods


# Tests that PeriodListWidget loads exam periods from the service and renders clickable rows.
def test_period_list_loads_periods_from_service(qtbot):
    service = MockAppService()
    widget = PeriodListWidget(service)

    qtbot.addWidget(widget)
    widget.refresh()

    assert "FALL_Aleph" in widget._rows_by_id
    assert "SPRI_Aleph" in widget._rows_by_id
    assert "FALL — Aleph" in widget._rows_by_id["FALL_Aleph"].text()


# Tests that clicking a period emits period_selected with the selected period id.
def test_period_list_emits_period_selected_signal(qtbot):
    service = MockAppService()
    widget = PeriodListWidget(service)

    qtbot.addWidget(widget)
    widget.refresh()

    with qtbot.waitSignal(widget.periods_selected, timeout=1000) as blocker:
        widget._rows_by_id["FALL_Aleph"].click()

    assert blocker.args == [["FALL_Aleph"]]


# Tests that clicking a period updates the selected period state.
def test_period_list_click_updates_selected_period(qtbot):
    service = MockAppService()
    widget = PeriodListWidget(service)

    qtbot.addWidget(widget)
    widget.refresh()

    widget._rows_by_id["SPRI_Aleph"].click()

    assert widget.selected_periods() == ["SPRI_Aleph"]


# Tests that clear_selection resets the selected period state.
def test_period_list_clear_selection_resets_state(qtbot):
    service = MockAppService()
    widget = PeriodListWidget(service)

    qtbot.addWidget(widget)
    widget.refresh()

    widget._rows_by_id["FALL_Aleph"].click()
    widget.clear_selection()

    assert widget.selected_periods() == []


# Tests that refresh handles an empty period list without crashing.
def test_period_list_refresh_with_empty_period_list(qtbot):
    service = MockAppService()
    service.periods = []

    widget = PeriodListWidget(service)

    qtbot.addWidget(widget)
    widget.refresh()

    assert widget.selected_periods() == []
    assert widget._rows_by_id == {}
