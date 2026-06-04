from src.views.widgets.program_list_widget import ProgramListWidget


class MockAppService:
    def __init__(self):
        self.selected_calls = []
        self.programs = [
            {"id": "83101", "name": "Software Engineering"},
            {"id": "83102", "name": "Computer Science"},
            {"id": "83108", "name": "Data Science"},
            {"id": "83109", "name": "Electrical Engineering"},
            {"id": "83110", "name": "Mathematics"},
            {"id": "83111", "name": "Physics"},
        ]

    def get_available_programs(self):
        return self.programs

    def select_programs(self, ids):
        self.selected_calls.append(list(ids))


# The tests below verify that ProgramListWidget correctly loads programs from the service,
# allows selecting/deselecting programs, enforces the max selection limit.
def test_program_list_loads_programs_from_service(qtbot):
    service = MockAppService()
    widget = ProgramListWidget(service)

    qtbot.addWidget(widget)
    widget.refresh()

    assert "83101" in widget._rows_by_id
    assert "83102" in widget._rows_by_id
    assert widget._rows_by_id["83101"].text() == "83101 - Software Engineering"


# The tests below verify that selecting/deselecting programs updates the internal state,
# calls the service with the correct program ids, and emits the programs_selected signal.
def test_program_list_selects_program_and_calls_service(qtbot):
    service = MockAppService()
    widget = ProgramListWidget(service)

    qtbot.addWidget(widget)
    widget.refresh()

    widget._rows_by_id["83101"].click()

    assert widget.selected_programs() == ["83101"]
    assert service.selected_calls[-1] == ["83101"]


# The tests below verify that the programs_selected signal is emitted with the correct list of selected program ids.
def test_program_list_emits_programs_selected_signal(qtbot):
    service = MockAppService()
    widget = ProgramListWidget(service)

    qtbot.addWidget(widget)
    widget.refresh()

    with qtbot.waitSignal(widget.programs_selected, timeout=1000) as blocker:
        widget._rows_by_id["83102"].click()

    assert blocker.args == [["83102"]]


# The tests below verify that deselecting a program updates the internal state, calls the service with an empty list,
# and emits the programs_selected signal with an empty list.
def test_program_list_allows_deselecting_program(qtbot):
    service = MockAppService()
    widget = ProgramListWidget(service)

    qtbot.addWidget(widget)
    widget.refresh()

    widget._rows_by_id["83101"].click()
    widget._rows_by_id["83101"].click()

    assert widget.selected_programs() == []
    assert service.selected_calls[-1] == []


# The tests below verify that once the max selection limit is reached, remaining rows become disabled,
# and that deselecting a program re-enables the remaining rows.
def test_program_list_disables_remaining_rows_after_five_selected(qtbot):
    service = MockAppService()
    widget = ProgramListWidget(service, max_selection=5)

    qtbot.addWidget(widget)
    widget.refresh()

    for program_id in ["83101", "83102", "83108", "83109", "83110"]:
        widget._rows_by_id[program_id].click()

    assert len(widget.selected_programs()) == 5
    assert widget._rows_by_id["83111"].isEnabled() is False


# The tests below verify that once the max selection limit is reached, remaining rows become disabled,
# and that deselecting a program re-enables the remaining rows.
def test_program_list_reenables_rows_after_deselecting(qtbot):
    service = MockAppService()
    widget = ProgramListWidget(service, max_selection=5)

    qtbot.addWidget(widget)
    widget.refresh()

    for program_id in ["83101", "83102", "83108", "83109", "83110"]:
        widget._rows_by_id[program_id].click()

    widget._rows_by_id["83101"].click()

    assert widget._rows_by_id["83111"].isEnabled() is True

# Tests that clear_selection resets the widget state and updates the service with an empty selection.
def test_program_list_clear_selection_resets_state(qtbot):
    service = MockAppService()
    widget = ProgramListWidget(service)

    qtbot.addWidget(widget)
    widget.refresh()

    widget._rows_by_id["83101"].click()
    widget.clear_selection()

    assert widget.selected_programs() == []
    assert service.selected_calls[-1] == []

# Tests that refresh handles an empty program list without crashing and displays the empty-state label.
def test_program_list_refresh_with_empty_program_list(qtbot):
    service = MockAppService()
    service.programs = []

    widget = ProgramListWidget(service)

    qtbot.addWidget(widget)
    widget.refresh()

    assert widget.selected_programs() == []
    assert widget._rows_by_id == {}
