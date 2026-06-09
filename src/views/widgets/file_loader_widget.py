from pathlib import Path

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QLabel, QFileDialog,
    QVBoxLayout, QHBoxLayout, QFrame, QSizePolicy,
)

import src.styles.theme as th
from src.presenter.i_app_service import IAppService
from src.views.shared_components.buttons import PrimaryButton

_FILE_FILTER = "Text Files (*.txt);;CSV Files (*.csv);;All Files (*)"
_DROP_ZONE_MIN_HEIGHT = 155
_TOGGLE_BTN_MIN_WIDTH = 72


class FilePathValidator:
    """Validates file paths before calling the service."""

    def validate(self, courses_paths: list[str], dates_path: str) -> None:
        if not courses_paths:
            raise ValueError("Courses file was not selected.")

        if not dates_path:
            raise ValueError("Dates file was not selected.")

        for path in courses_paths:
            if not Path(path).is_file():
                raise ValueError(f"Courses file does not exist: {Path(path).name}")

        if not Path(dates_path).is_file():
            raise ValueError("Dates file does not exist.")


class DropZoneCard(QFrame):
    """
    Clickable card that accepts files by browsing or drag-and-drop.
    In replace mode a new file replaces the current selection.
    In add mode a new file is appended to the list.
    Emits file_added(path) for each accepted file.
    """

    file_added = pyqtSignal(str)

    def __init__(self, icon: str, title: str, hint: str,
                 dialog_caption: str, single_file: bool = False, parent=None):
        super().__init__(parent)
        self._dialog_caption = dialog_caption
        # dates zone only ever needs one file
        self._single_file = single_file   
        self._paths: list[str] = []
        # controlled by the parent toggle
        self._replace_mode = True         

        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(_DROP_ZONE_MIN_HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._apply_idle_style()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(th.SPACING_SMALL)

        self._icon_lbl = QLabel(icon)
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        self._icon_lbl.setStyleSheet(
            f"font-size: {th.FONT_SIZE_XXL}px; background: transparent; border: none;"
        )

        self._title_lbl = QLabel(title)
        self._title_lbl.setAlignment(Qt.AlignCenter)
        self._title_lbl.setStyleSheet(
            f"color: {th.PRIMARY_COLOR}; font-size: {th.FONT_SIZE_MD}px;"
            f" font-weight: {th.FONT_WEIGHT_BOLD}; background: transparent; border: none;"
        )

        self._hint_lbl = QLabel(hint)
        self._hint_lbl.setAlignment(Qt.AlignCenter)
        self._hint_lbl.setWordWrap(True)
        self._hint_lbl.setStyleSheet(
            f"color: {th.TEXT_TERTIARY}; font-size: {th.FONT_SIZE_SM}px;"
            " background: transparent; border: none;"
        )

        self._file_lbl = QLabel("")
        self._file_lbl.setAlignment(Qt.AlignCenter)
        self._file_lbl.setWordWrap(True)
        self._file_lbl.setStyleSheet(
            f"color: {th.TEXT_MUTED}; font-size: {th.FONT_SIZE_XS}px;"
            " background: transparent; border: none;"
        )

        layout.addWidget(self._icon_lbl)
        layout.addWidget(self._title_lbl)
        layout.addWidget(self._hint_lbl)
        layout.addWidget(self._file_lbl)

    # Public API

    def paths(self) -> list[str]:
        return list(self._paths)

    def first_path(self) -> str:
        return self._paths[0] if self._paths else ""

    def set_replace_mode(self, replace: bool) -> None:
        self._replace_mode = replace

    def clear(self) -> None:
        self._paths.clear()
        self._file_lbl.setText("")
        self._apply_idle_style()

    # Opens a file dialog when the card is clicked
    def mousePressEvent(self, event):
        path, _ = QFileDialog.getOpenFileName(
            self, self._dialog_caption, "", _FILE_FILTER
        )
        if path:
            self._accept_file(path)

    # Accepts drag events that carry local file URLs
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._apply_hover_style()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        if self._paths:
            self._apply_selected_style()
        else:
            self._apply_idle_style()

    # Extracts dropped file paths and processes each one
    def dropEvent(self, event):
        for url in event.mimeData().urls():
            self._accept_file(url.toLocalFile())

    # Adds or replaces the file list based on the current mode, then emits file_added
    def _accept_file(self, path: str) -> None:
        if self._replace_mode or self._single_file:
            self._paths = [path]
        else:
            if path not in self._paths:
                self._paths.append(path)

        self._update_file_label()
        self._apply_selected_style()
        self.file_added.emit(path)

    def _update_file_label(self) -> None:
        if not self._paths:
            self._file_lbl.setText("")
        elif len(self._paths) == 1:
            self._file_lbl.setText(Path(self._paths[0]).name)
        else:
            self._file_lbl.setText(
                f"{Path(self._paths[0]).name} +{len(self._paths) - 1} more"
            )

    def _apply_idle_style(self) -> None:
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {th.BG_CARD};
                border: 2px dashed {th.BORDER_LIGHT};
                border-radius: {th.BUTTON_BORDER_RADIUS}px;
            }}
            QFrame:hover {{
                border-color: {th.PRIMARY_COLOR};
                background-color: {th.PRIMARY_LIGHT};
            }}
            """
        )

    def _apply_hover_style(self) -> None:
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {th.PRIMARY_LIGHT};
                border: 2px dashed {th.PRIMARY_COLOR};
                border-radius: {th.BUTTON_BORDER_RADIUS}px;
            }}
            """
        )

    def _apply_selected_style(self) -> None:
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {th.PRIMARY_LIGHT};
                border: 2px solid {th.PRIMARY_COLOR};
                border-radius: {th.BUTTON_BORDER_RADIUS}px;
            }}
            """
        )


class ValidationPanel(QFrame):
    """
    Checklist of requirements that must be met before generating a schedule.
    Call update_state() whenever any condition changes.
    """

    _ITEMS = [
        "Upload Courses File",
        "Upload Dates File",
        "Select at least 1 study program",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {th.BG_CARD};
                border: 1px solid {th.BORDER_LIGHT};
                border-radius: {th.BUTTON_BORDER_RADIUS}px;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            th.SPACING_MEDIUM, th.SPACING_MEDIUM,
            th.SPACING_MEDIUM, th.SPACING_MEDIUM,
        )
        layout.setSpacing(th.SPACING_SMALL)

        header_lbl = QLabel("Checklist")
        header_lbl.setStyleSheet(
            f"color: {th.TEXT_PRIMARY}; font-size: {th.FONT_SIZE_SM}px;"
            f" font-weight: {th.FONT_WEIGHT_BOLD}; background: transparent; border: none;"
        )
        layout.addWidget(header_lbl)

        self._item_rows: list[tuple[QLabel, QLabel]] = []
        for text in self._ITEMS:
            row = QHBoxLayout()
            row.setSpacing(th.SPACING_SMALL)

            dot = QLabel("○")
            dot.setFixedWidth(16)
            dot.setStyleSheet(
                f"color: {th.DANGER_COLOR}; font-size: {th.FONT_SIZE_MD}px;"
                " background: transparent; border: none;"
            )
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"color: {th.TEXT_SECONDARY}; font-size: {th.FONT_SIZE_SM}px;"
                " background: transparent; border: none;"
            )

            row.addWidget(dot)
            row.addWidget(lbl, stretch=1)
            layout.addLayout(row)
            self._item_rows.append((dot, lbl))

    # Updates each checklist item's icon and style to reflect its completion state.
    def update_state(self, courses: bool, dates: bool,
                     programs: bool, period: bool) -> None:
        for (dot, lbl), done in zip(self._item_rows, [courses, dates, programs, period]):
            if done:
                dot.setText("●")
                dot.setStyleSheet(
                    f"color: {th.SUCCESS_COLOR}; font-size: {th.FONT_SIZE_MD}px;"
                    " background: transparent; border: none;"
                )
                lbl.setStyleSheet(
                    f"color: {th.TEXT_TERTIARY}; font-size: {th.FONT_SIZE_SM}px;"
                    " text-decoration: line-through; background: transparent; border: none;"
                )
            else:
                dot.setText("○")
                dot.setStyleSheet(
                    f"color: {th.DANGER_COLOR}; font-size: {th.FONT_SIZE_MD}px;"
                    " background: transparent; border: none;"
                )
                lbl.setStyleSheet(
                    f"color: {th.TEXT_SECONDARY}; font-size: {th.FONT_SIZE_SM}px;"
                    " background: transparent; border: none;"
                )


class FileLoaderWidget(QWidget):
    """
    File loader with drop zones, a Replace/Add toggle, and a validation checklist.
    """

    # Signal emitted after files are loaded successfully.
    files_loaded = pyqtSignal()

    def __init__(
        self,
        service: IAppService,
        validator: FilePathValidator | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._service = service
        self._validator = validator or FilePathValidator()
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(th.SPACING_MEDIUM)

        # ── drop zones ─────────────────────────────────────────────────────
        zones_row = QHBoxLayout()
        zones_row.setSpacing(th.SPACING_MEDIUM)

        self._courses_zone = DropZoneCard(
            icon="📄",
            title="Courses File",
            hint="Drag & drop courses file here\n(or click to browse)\n\nCSV, Text (.csv, .txt)",
            dialog_caption="Select Courses File",
        )
        self._dates_zone = DropZoneCard(
            icon="📅",
            title="Dates File",
            hint="Drag & drop dates file here\n(or click to browse)\n\nCSV, Text (.csv, .txt)",
            dialog_caption="Select Dates File",
            single_file=True,   # dates zone always holds exactly one file
        )

        zones_row.addWidget(self._courses_zone)
        zones_row.addWidget(self._dates_zone)
        layout.addLayout(zones_row)

        # ── Replace / Add toggle ───────────────────────────────────────────
        self._replace_toggle = QPushButton("Replace")
        self._add_toggle = QPushButton("Add")
        self._replace_toggle.setCheckable(True)
        self._add_toggle.setCheckable(True)
        self._replace_toggle.setChecked(True)
        self._replace_toggle.setObjectName("toggleLeft")
        self._add_toggle.setObjectName("toggleRight")

        # Wrap both buttons in a pill container so each side gets its own radius
        _toggle_pill = QWidget()
        _toggle_pill.setObjectName("togglePill")
        _toggle_pill_layout = QHBoxLayout(_toggle_pill)
        _toggle_pill_layout.setContentsMargins(2, 2, 2, 2)
        _toggle_pill_layout.setSpacing(2)
        _toggle_pill_layout.addWidget(self._replace_toggle)
        _toggle_pill_layout.addWidget(self._add_toggle)
        _toggle_pill.setStyleSheet(self._toggle_style())

        toggle_row = QHBoxLayout()
        toggle_row.addStretch()
        toggle_row.addWidget(_toggle_pill)
        toggle_row.addStretch()
        layout.addLayout(toggle_row)

        # ── load button ────────────────────────────────────────────────────
        self._load_button = PrimaryButton("Load Files")
        self._load_button.setFixedHeight(32)
        load_row = QHBoxLayout()
        load_row.addStretch()
        load_row.addWidget(self._load_button)
        load_row.addStretch()
        layout.addLayout(load_row)

        # ── status message ─────────────────────────────────────────────────
        self._message_label = QLabel("")
        self._message_label.setWordWrap(True)
        self._message_label.setStyleSheet(
            f"color: {th.TEXT_TERTIARY}; font-size: {th.FONT_SIZE_SM}px;"
        )
        layout.addWidget(self._message_label)

        # ── validation panel ───────────────────────────────────────────────
        self.validation_panel = ValidationPanel()
        layout.addWidget(self.validation_panel)

        layout.addStretch()

    def _connect_signals(self) -> None:
        self._replace_toggle.clicked.connect(lambda: self._set_mode(replace=True))
        self._add_toggle.clicked.connect(lambda: self._set_mode(replace=False))
        self._courses_zone.file_added.connect(self._on_file_selected)
        self._dates_zone.file_added.connect(self._on_file_selected)
        self._load_button.clicked.connect(self._load_files)

    # Switches between Replace and Add mode and notifies the drop zones.
    def _set_mode(self, replace: bool) -> None:
        self._replace_toggle.setChecked(replace)
        self._add_toggle.setChecked(not replace)
        self._courses_zone.set_replace_mode(replace)
        self._dates_zone.set_replace_mode(replace)

    def _get_mode(self) -> str:
        return "replace" if self._replace_toggle.isChecked() else "append"

    # Refreshes the status message and validation panel when a file is selected.
    def _on_file_selected(self, _path: str) -> None:
        self._message_label.setText("")
        self._sync_validation()

    # Loads all queued courses files against the single dates file.
    # The first courses file uses the selected mode; additional ones always use append.
    def _load_files(self) -> None:
        try:
            self._set_loading_state(True)

            courses_paths = self._courses_zone.paths()
            dates_path = self._dates_zone.first_path()

            self._validator.validate(courses_paths, dates_path)

            mode = self._get_mode()
            for i, courses_path in enumerate(courses_paths):
                effective_mode = mode if i == 0 else "append"
                self._service.load_data(courses_path, dates_path, effective_mode)

            self._show_success("Files loaded successfully.")
            self.files_loaded.emit()
            self._sync_validation(courses=True, dates=True)

        except Exception as error:
            self._show_error(str(error))

        finally:
            self._set_loading_state(False)

    def _set_loading_state(self, is_loading: bool) -> None:
        self._load_button.setDisabled(is_loading)
        self._courses_zone.setDisabled(is_loading)
        self._dates_zone.setDisabled(is_loading)
        if is_loading:
            self._message_label.setText("Loading files...")

    def _show_success(self, message: str) -> None:
        self._message_label.setStyleSheet(
            f"color: {th.SUCCESS_COLOR}; font-size: {th.FONT_SIZE_SM}px;"
        )
        self._message_label.setText(message)

    def _show_error(self, message: str) -> None:
        self._message_label.setStyleSheet(
            f"color: {th.DANGER_COLOR}; font-size: {th.FONT_SIZE_SM}px;"
        )
        self._message_label.setText(f"Error: {message}")

    # Updates the file-related items in the validation panel.
    def _sync_validation(self, courses: bool = None, dates: bool = None,
                         programs: bool = False, period: bool = False) -> None:
        if courses is None:
            courses = bool(self._courses_zone.paths())
        if dates is None:
            dates = bool(self._dates_zone.first_path())
        self.validation_panel.update_state(courses, dates, programs, period)

    # Called by InputScreen to keep the programs/period items in the checklist in sync.
    def update_validation(self, programs: bool, period: bool) -> None:
        self._sync_validation(programs=programs, period=period)

    # Returns the stylesheet for the oval pill toggle container and its two buttons.
    def _toggle_style(self) -> str:
        return f"""
            QWidget#togglePill {{
                background-color: {th.BG_HOVER};
                border: 1px solid {th.BORDER_LIGHT};
                border-radius: {th.PILL_BORDER_RADIUS}px;
            }}
            QPushButton#toggleLeft, QPushButton#toggleRight {{
                background-color: transparent;
                color: {th.TEXT_TERTIARY};
                border: none;
                padding: {th.BUTTON_PADDING_VERTICAL_SM}px {th.SPACING_XL}px;
                font-family: {th.FONT_FAMILY};
                font-size: {th.FONT_SIZE_SM}px;
                font-weight: {th.FONT_WEIGHT_MEDIUM};
                border-radius: {th.PILL_BORDER_RADIUS}px;
                min-width: {_TOGGLE_BTN_MIN_WIDTH}px;
            }}
            QPushButton#toggleLeft:checked, QPushButton#toggleRight:checked {{
                background-color: {th.PRIMARY_COLOR};
                color: white;
                font-weight: {th.FONT_WEIGHT_BOLD};
            }}
            QPushButton#toggleLeft:hover:!checked, QPushButton#toggleRight:hover:!checked {{
                background-color: {th.BORDER_LIGHT};
                color: {th.TEXT_SECONDARY};
            }}
        """
