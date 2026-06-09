from PyQt5.QtCore import QObject, pyqtSignal

from src.views.input_screen.input_screen import InputScreen


class MockAppService:
    # Returns an empty program list for UI refresh tests.
    def get_available_programs(self):
        return []

    # Stores selected programs without validation for UI tests.
    def select_programs(self, ids):
        self.selected_programs = ids

    # Returns an empty period list for UI refresh tests.
    def get_periods(self):
        return []

    # Returns an empty course list for selected-program panel tests.
    def get_courses(self, program_id):
        return []

    # Updated IAppService compatibility: accepts optional programs_path.
    def load_data(self, courses_path, dates_path, mode, programs_path=None):
        self.loaded_data = (courses_path, dates_path, mode, programs_path)

    # Updated IAppService compatibility: blocking generation fallback.
    def generate(self):
        return 0

    # Updated IAppService compatibility: streaming generation used by EngineListener.
    def generate_stream(self):
        return iter([])

    # Updated IAppService compatibility: returns generated period ids.
    def get_period_ids(self):
        return []

    # Updated IAppService compatibility: returns schedules for one period.
    def get_period_schedules(self, period_id):
        return []

    # Updated IAppService compatibility: supports both global and per-period counts.
    def get_schedule_count(self, period_id=None):
        return 0

    # Updated IAppService compatibility: returns a schedule batch.
    def get_schedule_batch(self, start, limit):
        return []

    # Updated IAppService compatibility: returns one schedule by index.
    def get_schedule(self, index):
        return {}

    # Updated IAppService compatibility: exports one schedule by index.
    def export_schedule(self, index, path):
        self.exported_schedule = (index, path)

    # Updated IAppService compatibility: navigates within one period.
    def navigate(self, period_id, direction):
        return {"period_id": period_id, "direction": direction}

    # Updated IAppService compatibility: navigates the global schedule combination.
    def navigate_global(self, direction):
        return {"direction": direction}

    # Updated IAppService compatibility: exports the current combined selection.
    def export_current(self, path):
        self.exported_current = path

    # Updated IAppService compatibility: exports what is currently on screen using per-period indices.
    def export_by_period_indices(self, period_indices, path):
        self.exported_by_period = (period_indices, path)

    # Updated IAppService compatibility: returns the isolated schedule for one period at a local index.
    def get_period_schedule(self, period_id, index):
        return []

    # Updated IAppService compatibility: returns the current cross-period combination from disk.
    def get_current_combination(self):
        return []


class FakeGenerateWorker(QObject):
    period_ready = pyqtSignal(str)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    # Stores the service and exposes a start flag instead of running a real thread.
    def __init__(self, service):
        super().__init__()
        self.service = service
        self.started = False

    # Marks the worker as started without doing background work.
    def start(self):
        self.started = True


# Tests that the Generate button is hidden when the InputScreen is first created.
def test_generate_button_hidden_initially(qtbot):
    screen = InputScreen(MockAppService())
    qtbot.addWidget(screen)

    assert screen.generate_btn.isHidden()

# Tests that selecting only programs is enough to show the Generate button.
def test_generate_button_visible_after_program_only(qtbot):
    screen = InputScreen(MockAppService())
    qtbot.addWidget(screen)

    screen._on_programs_selected(["83101"])

    assert not screen.generate_btn.isHidden()
    assert screen.generate_btn.isEnabled()


# Tests that the Generate button becomes visible after selecting programs and a period.
def test_generate_button_visible_after_period_selected(qtbot):
    screen = InputScreen(MockAppService())
    qtbot.addWidget(screen)

    screen._on_programs_selected(["83101"])
    screen._on_period_selected("FALL_Aleph")

    assert not screen.generate_btn.isHidden()
    assert screen.generate_btn.isEnabled()


# Tests that clicking Generate disables the button and starts the background worker.
def test_generate_click_disables_button_and_starts_worker(qtbot, monkeypatch):
    monkeypatch.setattr(
        "src.views.input_screen.input_screen.GenerateWorker",
        FakeGenerateWorker,
    )

    screen = InputScreen(MockAppService())
    qtbot.addWidget(screen)

    screen._on_programs_selected(["83101"])
    screen._on_period_selected("FALL_Aleph")
    screen._on_generate_clicked()

    assert screen.generate_btn.isEnabled() is False
    assert screen._worker.started is True


# Tests that generation completion re-enables the button and emits the transition signal.
def test_generation_finished_reenables_button_and_switches_to_output(qtbot):
    screen = InputScreen(MockAppService())
    qtbot.addWidget(screen)

    screen._on_programs_selected(["83101"])
    screen._on_period_selected("FALL_Aleph")
    screen._generate_state.start_generation()
    screen._sync_generate_button_state()

    with qtbot.waitSignal(screen.switch_to_output, timeout=1000):
        screen._on_generation_finished(1)

    assert screen.generate_btn.isEnabled()


# Tests that worker errors re-enable the button and keep the user on the input screen.
def test_generation_error_reenables_button(qtbot):
    screen = InputScreen(MockAppService())
    qtbot.addWidget(screen)

    screen._on_programs_selected(["83101"])
    screen._on_period_selected("FALL_Aleph")
    screen._generate_state.start_generation()
    screen._sync_generate_button_state()

    screen._on_error("Generation failed")

    assert screen.generate_btn.isEnabled()


# Tests that removing the last selected program via the chip × hides the Generate button.
def test_removing_last_program_hides_generate_button(qtbot):
    from src.views.widgets.program_list_widget import ProgramItem, ProgramRowWidget

    screen = InputScreen(MockAppService())
    qtbot.addWidget(screen)

    screen._on_programs_selected(["83101"])
    screen._on_period_selected("FALL_Aleph")
    assert not screen.generate_btn.isHidden()

    # Give the program list enough state for remove_selection to emit programs_selected([])
    row = ProgramRowWidget(ProgramItem(program_id="83101", name="CS"))
    screen.program_list._rows_by_id["83101"] = row
    screen.program_list._selected_ids.add("83101")

    screen.selected_panel.program_removed.emit("83101")

    assert screen.generate_btn.isHidden()


# Tests that removing one of two selected programs keeps the Generate button visible.
def test_removing_one_of_two_programs_keeps_generate_button_visible(qtbot):
    from src.views.widgets.program_list_widget import ProgramItem, ProgramRowWidget

    screen = InputScreen(MockAppService())
    qtbot.addWidget(screen)

    screen._on_programs_selected(["83101", "83102"])
    screen._on_period_selected("FALL_Aleph")
    assert not screen.generate_btn.isHidden()

    for pid, name in [("83101", "CS"), ("83102", "Math")]:
        row = ProgramRowWidget(ProgramItem(program_id=pid, name=name))
        screen.program_list._rows_by_id[pid] = row
        screen.program_list._selected_ids.add(pid)

    screen.selected_panel.program_removed.emit("83101")

    assert not screen.generate_btn.isHidden()


# Tests that clicking generate starts the loading spinner.
def test_generate_click_starts_spinner(qtbot, monkeypatch):
    monkeypatch.setattr(
        "src.views.input_screen.input_screen.GenerateWorker",
        FakeGenerateWorker,
    )

    screen = InputScreen(MockAppService())
    qtbot.addWidget(screen)

    screen._on_programs_selected(["83101"])
    screen._on_period_selected("FALL_Aleph")
    
    assert not screen.spinner.is_running
    
    screen._on_generate_clicked()
    
    assert screen.spinner.is_running is True


# Tests that generation completion stops the loading spinner.
def test_generation_finished_stops_spinner(qtbot):
    screen = InputScreen(MockAppService())
    qtbot.addWidget(screen)

    screen._on_programs_selected(["83101"])
    screen._on_period_selected("FALL_Aleph")
    screen._generate_state.start_generation()
    screen.spinner.start()

    screen._on_generation_finished(1)
    
    assert screen.spinner.is_running is False


# Tests that generation error shows the error banner and stops the spinner.
def test_generation_error_shows_banner_and_stops_spinner(qtbot):
    screen = InputScreen(MockAppService())
    qtbot.addWidget(screen)

    screen._on_programs_selected(["83101"])
    screen._on_period_selected("FALL_Aleph")
    screen._generate_state.start_generation()
    screen.spinner.start()

    screen._on_error("Test constraint error")
    
    assert screen.spinner.is_running is False
    assert not screen.error_banner.isHidden()
    assert "Test constraint error" in screen.error_banner.message_label.text()


# Tests that clicking generate hides any previous error banner.
def test_generate_click_hides_error_banner(qtbot, monkeypatch):
    monkeypatch.setattr(
        "src.views.input_screen.input_screen.GenerateWorker",
        FakeGenerateWorker,
    )

    screen = InputScreen(MockAppService())
    qtbot.addWidget(screen)

    screen.error_banner.show_error("Old error")
    assert not screen.error_banner.isHidden()

    screen._on_programs_selected(["83101"])
    screen._on_period_selected("FALL_Aleph")
    screen._on_generate_clicked()

    assert screen.error_banner.isHidden()


# Tests that loading new files resets the entire screen state.
def test_files_loaded_resets_screen_state(qtbot):
    screen = InputScreen(MockAppService())
    qtbot.addWidget(screen)

    screen._on_programs_selected(["83101"])
    screen._on_period_selected("FALL_Aleph")
    
    assert not screen.selected_panel.isHidden()
    assert not screen.period_list.isHidden()
    assert not screen.period_editor.isHidden()
    assert not screen.generate_btn.isHidden()

    screen._on_files_loaded()

    assert screen.selected_panel.isHidden()
    assert screen.period_list.isHidden()
    assert screen.period_editor.isHidden()
    assert screen.generate_btn.isHidden()
    assert screen._generate_state.has_selected_programs is False
    assert screen._generate_state.has_viewed_period is False

