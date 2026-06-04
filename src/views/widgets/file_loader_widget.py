from pathlib import Path

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QLabel, QFileDialog,
    QVBoxLayout, QHBoxLayout, QRadioButton,
    QButtonGroup
)

from src.presenter.i_app_service import IAppService


class FilePathValidator:
    """Validates file paths before calling the service."""

    def validate(self, courses_path: str, dates_path: str) -> None:
        if not courses_path:
            raise ValueError("Courses file was not selected.")

        if not dates_path:
            raise ValueError("Dates file was not selected.")

        if not Path(courses_path).is_file():
            raise ValueError("Courses file does not exist.")

        if not Path(dates_path).is_file():
            raise ValueError("Dates file does not exist.")


class FileLoaderWidget(QWidget):
    # Signal emitted after files are loaded successfully.
    files_loaded = pyqtSignal()

    def __init__(
        self,
        service: IAppService,
        validator: FilePathValidator | None = None,
        parent=None
    ):
        super().__init__(parent)

        self._service = service
        self._validator = validator or FilePathValidator()

        self._courses_path = ""
        self._dates_path = ""

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        # UI Elements
        self._courses_label = QLabel("No courses file selected")
        self._dates_label = QLabel("No dates file selected")
        self._message_label = QLabel("")

        # Buttons: Courses, Dates, Load
        self._select_courses_button = QPushButton("Select Courses File")
        self._select_dates_button = QPushButton("Select Dates File")
        self._load_button = QPushButton("Load Files")

        # Mode selection: Replace or Append
        self._replace_radio = QRadioButton("Replace")
        self._append_radio = QRadioButton("Append")
        self._replace_radio.setChecked(True)

        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._replace_radio)
        self._mode_group.addButton(self._append_radio)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(self._replace_radio)
        mode_layout.addWidget(self._append_radio)

        layout = QVBoxLayout()
        layout.addWidget(self._select_courses_button)
        layout.addWidget(self._courses_label)
        layout.addWidget(self._select_dates_button)
        layout.addWidget(self._dates_label)
        layout.addLayout(mode_layout)
        layout.addWidget(self._load_button)
        layout.addWidget(self._message_label)

        self.setLayout(layout)

    def _connect_signals(self) -> None:
        # Connect button clicks to their respective handlers
        self._select_courses_button.clicked.connect(self._choose_courses_file)
        self._select_dates_button.clicked.connect(self._choose_dates_file)
        self._load_button.clicked.connect(self._load_files)

    def _choose_courses_file(self) -> None:
        # Open file dialog to select courses file
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Courses File",
            "",
            "CSV Files (*.csv);;Text Files (*.txt);;All Files (*)"
        )

        # If a file was selected, update the path and label
        if path:
            self._courses_path = path
            self._courses_label.setText(path)

    def _choose_dates_file(self) -> None:
        # Open file dialog to select dates file
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Dates File",
            "",
            "CSV Files (*.csv);;Text Files (*.txt);;All Files (*)"
        )

        # If a file was selected, update the path and label
        if path:
            self._dates_path = path
            self._dates_label.setText(path)

    def _get_mode(self) -> str:
        # Determine the selected mode based on the radio buttons
        if self._append_radio.isChecked():
            return "append"
        return "replace"

    def _load_files(self) -> None:
        # Validate file paths and call the service to load data
        try:
            self._set_loading_state(True)

            self._validator.validate(self._courses_path, self._dates_path)

            self._service.load_data(
                self._courses_path,
                self._dates_path,
                self._get_mode()
            )

            self._show_success("Files loaded successfully.")
            self.files_loaded.emit()

        except Exception as error:
            self._show_error(str(error))

        finally:
            self._set_loading_state(False)

    def _set_loading_state(self, is_loading: bool) -> None:
        # Disable UI elements while loading to prevent multiple clicks
        self._load_button.setDisabled(is_loading)
        self._select_courses_button.setDisabled(is_loading)
        self._select_dates_button.setDisabled(is_loading)
        self._replace_radio.setDisabled(is_loading)
        self._append_radio.setDisabled(is_loading)

        if is_loading:
            self._message_label.setText("Loading files...")

    def _show_success(self, message: str) -> None:
        self._message_label.setText(message)

    def _show_error(self, message: str) -> None:
        self._message_label.setText(f"Error: {message}")