"""
DayDetailDialog — popup shown when the user clicks an exam badge.

Each exam is a collapsible card row:
  ┌────────────────────────────────────────────────────┐
  │ [CODE]  Course Name                    [Type badge] │
  │ Programs Affected (N)                           ▲/▼ │
  │   • Full Program Name (AB)                       AB  │
  │   • …                                                │
  └────────────────────────────────────────────────────┘

Left border colour: indigo for Required, green for Elective.
Programs section is expanded by default; the arrow toggles it.
"""

from __future__ import annotations

from datetime import date as date_type

from PyQt5.QtCore import QEvent, QPoint, Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.styles.day_detail_dialog_style import (
    CARD_STYLE,
    CLOSE_BTN_STYLE,
    EDIT_MODE_MAX_WIDTH,
    EDIT_MODE_MIN_WIDTH,
    COURSE_CODE_ELECTIVE_STYLE,
    COURSE_CODE_REQUIRED_STYLE,
    COURSE_NAME_INLINE_STYLE,
    EXAM_ROW_ELECTIVE_BORDER,
    EXAM_ROW_REQUIRED_BORDER,
    FOOTER_STYLE,
    MINI_BADGE_ELECTIVE_STYLE,
    MINI_BADGE_REQUIRED_STYLE,
    PROGRAM_BULLET_STYLE,
    PROGRAMS_COUNT_STYLE,
    ROOM_BULLET_STYLE,
    ROOM_CAPACITY_STYLE,
    ROOM_SECTION_LABEL_STYLE,
    ROOM_SEPARATOR_STYLE,
    TIME_SLOT_STYLE,
    TITLE_STYLE,
    exam_row_style,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_date(value) -> str:
    """Format an exam date as DD/MM/YYYY; passes strings through unchanged."""
    if isinstance(value, date_type):
        return value.strftime("%d/%m/%Y")
    return str(value) if value else "—"


def _is_elective(exam: dict) -> bool:
    t = str(exam.get("type", "Obligatory")).strip().lower()
    return "elective" in t or "elect" in t


# ---------------------------------------------------------------------------
# _ExamRow — one collapsible card per exam
# ---------------------------------------------------------------------------

class _ExamRow(QFrame):
    """
    Card row for a single exam.

    Layout:
      top row : [CODE]  Name                    [Type badge]
      prog row: Programs Affected (N)
      list    : • Full Name (AB)                          AB
                  …
      (edit mode only)
      edit row: [Edit]
    """

    edit_requested = pyqtSignal(dict)   # emitted only in edit_mode

    def __init__(
        self,
        exam: dict,
        program_names: dict[str, str],
        edit_mode: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._exam     = exam
        elective   = _is_elective(exam)
        border_clr = EXAM_ROW_ELECTIVE_BORDER if elective else EXAM_ROW_REQUIRED_BORDER
        self.setStyleSheet(exam_row_style(border_clr))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(6)

        # ── Time slot row (edit mode: clock icon + time) ─────────────
        if edit_mode and exam.get("time_slot"):
            from src.views.output_screen.edit_exam_dialog import _slot_label
            slot_row = QHBoxLayout()
            slot_row.setSpacing(6)
            slot_row.setContentsMargins(0, 0, 0, 0)
            clock_lbl = QLabel("🕐")
            clock_lbl.setStyleSheet("font-size: 14px; background: transparent;")
            time_lbl = QLabel(_slot_label(exam.get("time_slot")))
            time_lbl.setStyleSheet(
                "color: #334155; font-size: 14px; font-weight: 600; background: transparent;"
            )
            slot_row.addWidget(clock_lbl)
            slot_row.addWidget(time_lbl)
            slot_row.addStretch()
            outer.addLayout(slot_row)

        # ── Top row: code  name  |  badge ────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(6)
        top.setContentsMargins(0, 0, 0, 0)

        code_lbl = QLabel(str(exam.get("course_number", "—")))
        code_lbl.setStyleSheet(
            COURSE_CODE_ELECTIVE_STYLE if elective else COURSE_CODE_REQUIRED_STYLE
        )

        name_lbl = QLabel(str(exam.get("course_name", "—")))
        name_lbl.setStyleSheet(COURSE_NAME_INLINE_STYLE)

        badge_lbl = QLabel("Elective" if elective else "Required")
        badge_lbl.setAlignment(Qt.AlignCenter)
        badge_lbl.setStyleSheet(
            MINI_BADGE_ELECTIVE_STYLE if elective else MINI_BADGE_REQUIRED_STYLE
        )

        top.addWidget(code_lbl)
        top.addSpacing(4)
        top.addWidget(name_lbl)
        top.addStretch()
        top.addWidget(badge_lbl)
        outer.addLayout(top)

        # ── "Programs Affected (N)" label ────────────────────────────
        programs = list(exam.get("programs") or [])
        n = len(programs)

        count_lbl = QLabel(f"Programs Affected ({n})")
        count_lbl.setStyleSheet(PROGRAMS_COUNT_STYLE)
        outer.addWidget(count_lbl)

        # ── Program bullet list (always visible) ──────────────────────
        for pid in programs:
            display_full = program_names.get(str(pid), str(pid))

            bullet = QLabel(f"• {display_full}")
            bullet.setStyleSheet(PROGRAM_BULLET_STYLE)
            outer.addWidget(bullet)

        # ── Room scheduling info (only present in room-scheduling mode) ──
        # Keys "time_slot", "rooms_display", "num_students", and "total_capacity" are
        # added by _format_schedule_rows() only when placement.is_room_based.
        # Date-only placements omit these keys, so no room section is rendered,
        # keeping the card layout identical to what it was before this feature.
        time_slot     = exam.get("time_slot")
        rooms_display = exam.get("rooms_display", [])  # pre-formatted strings

        if time_slot or rooms_display:
            # Separator between programs and room info
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet(ROOM_SEPARATOR_STYLE)
            outer.addWidget(sep)

        if time_slot:
            slot_lbl = QLabel(f"Time slot: {time_slot}")
            slot_lbl.setStyleSheet(TIME_SLOT_STYLE)
            outer.addWidget(slot_lbl)

        if rooms_display:
            rooms_header = QLabel("Assigned rooms")
            rooms_header.setStyleSheet(ROOM_SECTION_LABEL_STYLE)
            outer.addWidget(rooms_header)

            for room_str in rooms_display:
                room_line = QLabel(room_str)
                room_line.setStyleSheet(ROOM_BULLET_STYLE)
                outer.addWidget(room_line)

            num_students   = exam.get("num_students", 0)
            total_capacity = exam.get("total_capacity", 0)
            capacity_lbl   = QLabel(
                f"Capacity: {total_capacity} seats for {num_students} students"
            )
            capacity_lbl.setStyleSheet(ROOM_CAPACITY_STYLE)
            outer.addWidget(capacity_lbl)

        # ── Edit button (visible only in edit mode) ───────────────────
        if edit_mode:
            edit_row = QHBoxLayout()
            edit_row.setContentsMargins(0, 4, 0, 0)
            edit_row.addStretch()
            edit_btn = QPushButton("Edit")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background: #4338CA; color: #FFFFFF;
                    border: none; border-radius: 8px;
                    padding: 5px 18px; font-size: 13px; font-weight: 600;
                }
                QPushButton:hover { background: #3730A3; }
            """)
            edit_btn.clicked.connect(lambda: self.edit_requested.emit(self._exam))
            edit_row.addWidget(edit_btn)
            outer.addLayout(edit_row)


# ---------------------------------------------------------------------------
# DayDetailDialog
# ---------------------------------------------------------------------------

class DayDetailDialog(QDialog):
    """
    Frameless modal dialog listing all exams for a given day.

    Args:
        exams:         list of exam dicts for the clicked day.
        exam_date:     the date shown in the title.
        program_names: optional {program_id: display_name} mapping.
        anchor_pos:    global QPoint to position the dialog (bottom of clicked cell).
        edit_mode:     when True each exam row shows an "Edit" button.
        parent:        optional parent widget.
    """

    # Emitted when the user clicks "Edit" on a specific exam row (edit_mode only).
    edit_requested = pyqtSignal(dict)

    def __init__(
        self,
        exams: list[dict],
        exam_date=None,
        program_names: dict[str, str] | None = None,
        anchor_pos: QPoint | None = None,
        edit_mode: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._exams         = exams or []
        self._exam_date     = exam_date
        self._program_names = program_names or {}
        self._edit_mode     = edit_mode
        self._build_ui()

        # Position after the widget is shown so geometry is known.
        QTimer.singleShot(0, lambda: QApplication.instance().installEventFilter(self))
        QTimer.singleShot(0, self._center_on_screen)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._clamp_to_screen()

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        geo    = self.frameGeometry()
        if self._edit_mode:
            # In edit mode: place on the LEFT half so the edit dialog can sit to the right.
            x = screen.left() + (screen.width() // 2 - geo.width()) // 2
        else:
            x = screen.left() + (screen.width() - geo.width()) // 2
        y = screen.top()  + (screen.height() - geo.height()) // 2
        self.move(max(screen.left(), x), max(screen.top(), y))

    def _clamp_to_screen(self) -> None:
        """Nudge the dialog inward if it would be clipped by a screen edge."""
        screen = QApplication.primaryScreen().availableGeometry()
        geo = self.frameGeometry()
        x, y = geo.x(), geo.y()
        if geo.bottom() > screen.bottom():
            y = screen.bottom() - geo.height()
        if geo.right() > screen.right():
            x = screen.right() - geo.width()
        x = max(x, screen.left())
        y = max(y, screen.top())
        if x != geo.x() or y != geo.y():
            self.move(x, y)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(False)
        if self._edit_mode:
            self.setMinimumWidth(EDIT_MODE_MIN_WIDTH)
            self.setMaximumWidth(EDIT_MODE_MAX_WIDTH)
        else:
            self.setMinimumWidth(340)
            self.setMaximumWidth(440)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── Card ──────────────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("dialogCard")
        card.setStyleSheet(CARD_STYLE)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(10)

        # ── Header: "Exams on DD/MM/YYYY"  [✕] ───────────────────────
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel(f"Exams on {_format_date(self._exam_date)}")
        title_lbl.setStyleSheet(TITLE_STYLE)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(CLOSE_BTN_STYLE)
        close_btn.clicked.connect(self.close)

        header.addWidget(title_lbl)
        header.addStretch()
        header.addWidget(close_btn)
        card_layout.addLayout(header)

        # ── Scrollable exam rows ──────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")
        # No fixed max-height: the dialog is clamped to the screen by
        # _clamp_to_screen(), and the scroll area expands to show all exams.
        screen_h = QApplication.primaryScreen().availableGeometry().height()
        scroll.setMaximumHeight(int(screen_h * 0.75))

        rows_widget = QWidget()
        rows_widget.setStyleSheet("background: transparent;")
        rows_layout = QVBoxLayout(rows_widget)
        rows_layout.setContentsMargins(0, 0, 0, 0)
        rows_layout.setSpacing(8)

        for exam in self._exams:
            row = _ExamRow(exam, self._program_names, edit_mode=self._edit_mode)
            if self._edit_mode:
                row.edit_requested.connect(self.edit_requested)
            rows_layout.addWidget(row)

        rows_layout.addStretch()
        scroll.setWidget(rows_widget)
        card_layout.addWidget(scroll)

        # ── Footer: "🔗  N exams on this day" ────────────────────────
        n     = len(self._exams)
        noun  = "exam" if n == 1 else "exams"
        footer = QLabel(f"{n} {noun} on this day")
        footer.setStyleSheet(FOOTER_STYLE)
        card_layout.addWidget(footer)

        outer.addWidget(card)

    # ------------------------------------------------------------------
    # Outside-click / close handling
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.MouseButtonPress:
            global_pos = event.globalPos()
            # Close if click is outside this dialog's geometry
            if not self.geometry().contains(global_pos):
                self.close()
                return False
        return super().eventFilter(obj, event)

    def closeEvent(self, event) -> None:
        QApplication.instance().removeEventFilter(self)
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Helpers (static so tests can call DayDetailDialog._format_date)
    # ------------------------------------------------------------------

    @staticmethod
    def _format_date(value) -> str:
        """Format an exam date as DD/MM/YYYY; passes strings through unchanged."""
        return _format_date(value)
