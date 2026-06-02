import pytest

from src.views.widgets.file_loader_widget import FileLoaderWidget


class MockFileLoadingService:
    def __init__(self):
        self.calls = []

    def load_data(self, courses_path: str, dates_path: str, mode: str) -> None:
        self.calls.append((courses_path, dates_path, mode))


# Verify that clicking "Load Files" calls the service with replace mode.
def test_file_loader_calls_service_with_replace_mode(qtbot, tmp_path):
    courses_file = tmp_path / "courses.csv"
    dates_file = tmp_path / "dates.csv"

    courses_file.write_text("dummy courses data")
    dates_file.write_text("dummy dates data")

    service = MockFileLoadingService()
    widget = FileLoaderWidget(service)

    qtbot.addWidget(widget)

    widget._courses_path = str(courses_file)
    widget._dates_path = str(dates_file)
    widget._replace_radio.setChecked(True)

    widget._load_button.click()

    assert service.calls == [
        (str(courses_file), str(dates_file), "replace")
    ]


# Verify that clicking "Load Files" calls the service with append mode.
def test_file_loader_calls_service_with_append_mode(qtbot, tmp_path):
    courses_file = tmp_path / "courses.csv"
    dates_file = tmp_path / "dates.csv"

    courses_file.write_text("dummy courses data")
    dates_file.write_text("dummy dates data")

    service = MockFileLoadingService()
    widget = FileLoaderWidget(service)

    qtbot.addWidget(widget)

    widget._courses_path = str(courses_file)
    widget._dates_path = str(dates_file)
    widget._append_radio.setChecked(True)

    widget._load_button.click()

    assert service.calls == [
        (str(courses_file), str(dates_file), "append")
    ]


# Verify that the widget emits files_loaded after a successful load.
def test_file_loader_emits_files_loaded_on_success(qtbot, tmp_path):
    courses_file = tmp_path / "courses.csv"
    dates_file = tmp_path / "dates.csv"

    courses_file.write_text("dummy courses data")
    dates_file.write_text("dummy dates data")

    service = MockFileLoadingService()
    widget = FileLoaderWidget(service)

    qtbot.addWidget(widget)

    widget._courses_path = str(courses_file)
    widget._dates_path = str(dates_file)

    with qtbot.waitSignal(widget.files_loaded, timeout=1000):
        widget._load_button.click()


# Verify that a success message is displayed after loading files successfully.
def test_file_loader_shows_success_message_after_load(qtbot, tmp_path):
    courses_file = tmp_path / "courses.csv"
    dates_file = tmp_path / "dates.csv"

    courses_file.write_text("dummy courses data")
    dates_file.write_text("dummy dates data")

    service = MockFileLoadingService()
    widget = FileLoaderWidget(service)

    qtbot.addWidget(widget)

    widget._courses_path = str(courses_file)
    widget._dates_path = str(dates_file)

    widget._load_button.click()

    assert widget._message_label.text() == "Files loaded successfully."