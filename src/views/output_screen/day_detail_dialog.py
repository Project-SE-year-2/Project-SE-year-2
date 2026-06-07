"""
DayDetailDialog — shown when the user clicks an exam badge on the calendar.
Displays: course number, course name, type badge, affected programs chips,
exam date, semester, and moed.
"""

from datetime import date as date_type

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.views.shared_components.type_badge import TypeBadge
from src.styles.day_detail_dialog_style import CARD_STYLE, CLOSE_BTN_STYLE, TITLE_STYLE
from src.styles.shared_styles import (
    get_section_label_style,
    get_value_label_style,
    get_divider_style,
    get_program_chip_style,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _section_label(text: str) -> QLabel:
    """Muted label used as a field caption."""
    lbl = QLabel(text)
    lbl.setStyleSheet(get_section_label_style())
    return lbl


def _value_label(text: str) -> QLabel:
    """Bright label used to display a field value."""
    lbl = QLabel(text)
    lbl.setStyleSheet(get_value_label_style())
    lbl.setWordWrap(True)
    return lbl


def _divider() -> QFrame:
    """Thin horizontal line used as a separator."""
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet(get_divider_style())
    return line


def _program_chip(display_name: str) -> QLabel:
    """Small chip showing a program display name."""
    chip = QLabel(display_name)
    chip.setAlignment(Qt.AlignCenter)
    chip.setFixedHeight(28)
    chip.setStyleSheet(get_program_chip_style())
    return chip


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

class DayDetailDialog(QDialog):
    """
    Modal dialog that shows full details for one exam entry.

    Args:
        exam_data: dict emitted by ScheduleCalendarWidget.exam_clicked
                   Keys: course_number, course_name, type, programs (list[str]),
                         exam_date, semester, moed
        program_names: optional mapping {program_id: display_name}; falls back
                       to the raw ID when a name is not found.
        parent: optional parent widget
    """

    def __init__(self, exam_data: dict, program_names: dict[str, str] | None = None, parent=None):
        """program_names is a mapping from program ID to display name, used to show nicer labels in the chips."""
        super().__init__(parent)
        self._data = exam_data
        self._program_names = program_names or {}
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Builds the dialog's UI based on the exam data."""
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumWidth(340)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── Card ──────────────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("dialogCard")
        card.setStyleSheet(CARD_STYLE)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 24)
        card_layout.setSpacing(14)

        # ── Header row ────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Exam Details")
        title.setStyleSheet(TITLE_STYLE)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(CLOSE_BTN_STYLE)
        close_btn.clicked.connect(self.accept)

        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(close_btn)
        card_layout.addLayout(header_row)

        # ── Divider ───────────────────────────────────────────────────
        card_layout.addWidget(_divider())

        # ── Fields ───────────────────────────────────────────────────
        course_number = self._data.get("course_number", "—")
        course_name   = self._data.get("course_name",   "—")
        type_str      = self._data.get("type",          "Obligatory")
        programs      = self._data.get("programs",      [])
        exam_date     = self._data.get("exam_date")
        semester      = self._data.get("semester",      "—")
        moed          = self._data.get("moed",          "—")

        card_layout.addLayout(self._field_row(_section_label("Course Number"),
                                               _value_label(str(course_number))))
        card_layout.addLayout(self._field_row(_section_label("Course Name"),
                                               _value_label(str(course_name))))
        card_layout.addLayout(self._type_row(type_str))
        card_layout.addLayout(self._programs_row(programs, self._program_names))
        card_layout.addLayout(self._field_row(_section_label("Exam Date"),
                                               _value_label(self._format_date(exam_date))))
        card_layout.addLayout(self._field_row(_section_label("Semester"),
                                               _value_label(str(semester))))
        card_layout.addLayout(self._field_row(_section_label("Moed"),
                                               _value_label(str(moed))))

        outer.addWidget(card)

    # ------------------------------------------------------------------
    # Row builders
    # ------------------------------------------------------------------

    @staticmethod
    def _field_row(caption: QLabel, value: QLabel) -> QHBoxLayout:
        """Two-column row: muted caption on the left, bright value on the right."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        caption.setFixedWidth(130)
        row.addWidget(caption, 0, Qt.AlignTop)
        row.addWidget(value, 1)
        return row

    @staticmethod
    def _type_row(type_str: str) -> QHBoxLayout:
        """Row with the TypeBadge widget."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        caption = _section_label("Type")
        caption.setFixedWidth(130)

        row.addWidget(caption, 0, Qt.AlignVCenter)
        row.addWidget(TypeBadge(type_str), 0, Qt.AlignVCenter)
        row.addStretch()
        return row

    @staticmethod
    def _programs_row(programs: list, program_names: dict) -> QHBoxLayout:
        """Row with one chip per affected program, showing display name when available."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        caption = _section_label("Affected Programs")
        caption.setFixedWidth(130)
        row.addWidget(caption, 0, Qt.AlignVCenter)

        chips_widget = QWidget()
        chips_layout = QHBoxLayout(chips_widget)
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(6)

        for pid in programs:
            display = program_names.get(str(pid), str(pid))
            chips_layout.addWidget(_program_chip(display))
        chips_layout.addStretch()

        row.addWidget(chips_widget, 1)
        return row

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_date(value) -> str:
        if isinstance(value, date_type):
            return value.strftime("%d/%m/%Y")
        return str(value) if value else "—"
