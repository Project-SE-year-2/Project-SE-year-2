from src.views.widgets.selected_programs_panel import SelectedProgramsPanel


class MockAppService:
    def __init__(self):
        self.calls = []
        self.courses_by_program = {
            "83101": [
                {
                    "number": "101",
                    "name": "Intro to Programming",
                    "year": 1,
                    "semester": "FALL",
                    "type": "Obligatory",
                    "evaluation": "Exam",
                },
                {
                    "number": "102",
                    "name": "Discrete Math",
                    "year": 1,
                    "semester": "FALL",
                    "type": "Elective",
                    "evaluation": "Exam",
                },
            ],
            "83102": [
                {
                    "number": "201",
                    "name": "Data Structures",
                    "year": 2,
                    "semester": "SPRI",
                    "type": "Obligatory",
                    "evaluation": "Exam",
                },
            ],
        }

    def get_courses(self, program_id):
        self.calls.append(program_id)
        return self.courses_by_program.get(program_id, [])


# Tests that refresh creates one card for each selected program.
def test_selected_programs_panel_renders_selected_program_cards(qtbot):
    service = MockAppService()
    panel = SelectedProgramsPanel(service)

    qtbot.addWidget(panel)
    panel.refresh(["83101", "83102"])

    assert "83101" in panel._cards_by_program_id
    assert "83102" in panel._cards_by_program_id


# Tests that the panel asks the service for courses of selected programs.
def test_selected_programs_panel_loads_courses_from_service(qtbot):
    service = MockAppService()
    panel = SelectedProgramsPanel(service)

    qtbot.addWidget(panel)
    panel.refresh(["83101"])

    assert service.calls == ["83101"]


# Tests that course results are cached and not loaded repeatedly from the service.
def test_selected_programs_panel_uses_cache_for_repeated_program(qtbot):
    service = MockAppService()
    panel = SelectedProgramsPanel(service)

    qtbot.addWidget(panel)
    panel.refresh(["83101"])
    panel.refresh(["83101"])

    assert service.calls == ["83101"]
    assert panel.cached_program_ids() == ["83101"]


# Tests that clear removes all currently displayed program cards.
def test_selected_programs_panel_clear_removes_cards(qtbot):
    service = MockAppService()
    panel = SelectedProgramsPanel(service)

    qtbot.addWidget(panel)
    panel.refresh(["83101"])
    panel.clear()

    assert panel._cards_by_program_id == {}


# Tests that clear_cache removes cached course data.
def test_selected_programs_panel_clear_cache_resets_cache(qtbot):
    service = MockAppService()
    panel = SelectedProgramsPanel(service)

    qtbot.addWidget(panel)
    panel.refresh(["83101"])
    panel.clear_cache()

    assert panel.cached_program_ids() == []


# Tests that refresh with an empty selection does not crash and shows no cards.
def test_selected_programs_panel_refresh_with_empty_selection(qtbot):
    service = MockAppService()
    panel = SelectedProgramsPanel(service)

    qtbot.addWidget(panel)
    panel.refresh([])

    assert panel._cards_by_program_id == {}
