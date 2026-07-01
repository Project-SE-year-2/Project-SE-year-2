"""
EditExamDialog — floating edit panel opened when the user clicks an exam day
while "Edit Schedule" mode is active.
"""

from __future__ import annotations

import math
from datetime import date as date_type

from PyQt5.QtCore import QDate, QEvent, QPoint, Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.styles.edit_exam_dialog_style import (
    EDIT_DIALOG_MAX_WIDTH,
    EDIT_DIALOG_MIN_HEIGHT,
    EDIT_DIALOG_MIN_WIDTH,
    ASSIGN_BTN_STYLE,
    ASSIGNED_BTN_STYLE,
    ASSIGNED_ROOMS_LABEL_STYLE,
    AVAIL_ROOMS_LABEL_STYLE,
    CANCEL_BTN_STYLE,
    CAPACITY_HINT_STYLE,
    CARD_STYLE,
    CHIP_LABEL_STYLE,
    CHIP_REMOVE_STYLE,
    CHIP_STYLE,
    CLEAR_ALL_BTN_STYLE,
    CLOSE_BTN_STYLE,
    COMBO_STYLE,
    COURSE_META_STYLE,
    COURSE_NAME_STYLE,
    COURSE_TIME_STYLE,
    DATE_EDIT_STYLE,
    DIALOG_TITLE_STYLE,
    FIELD_LABEL_STYLE,
    FILTER_COMBO_STYLE,
    NOTICE_STYLE,
    SAVE_BTN_STYLE,
    SEARCH_STYLE,
    SECTION_TITLE_STYLE,
    SEPARATOR_STYLE,
    TABLE_STYLE,
    TIME_DOT_STYLE,
    TYPE_BADGE_ELECTIVE_STYLE,
    TYPE_BADGE_REQUIRED_STYLE,
    VIEW_IN_DAY_BTN_STYLE,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TIME_SLOT_DISPLAY: dict[str, str] = {
    "MORNING":   "09:00 – 12:00",
    "AFTERNOON": "12:30 – 15:30",
    "EVENING":   "16:00 – 19:00",
}

_DISPLAY_TO_SLOT: dict[str, str] = {v: k for k, v in _TIME_SLOT_DISPLAY.items()}


def _slot_label(slot_str: str | None) -> str:
    if slot_str is None:
        return "—"
    return _TIME_SLOT_DISPLAY.get(slot_str.upper(), slot_str)


def _format_date(value) -> str:
    if isinstance(value, date_type):
        return value.strftime("%d/%m/%Y")
    return str(value) if value else "—"


def _is_elective(exam: dict) -> bool:
    t = str(exam.get("type", "Obligatory")).strip().lower()
    return "elective" in t or "elect" in t


# ---------------------------------------------------------------------------
# _RoomChip — removable pill for an assigned room
# ---------------------------------------------------------------------------

class _RoomChip(QFrame):
    """Small pill chip showing a room ID with a remove button."""

    removed = pyqtSignal(str)  # emits room_key

    def __init__(self, room_key: str, label: str, parent=None):
        super().__init__(parent)
        self._room_key = room_key
        self.setStyleSheet(CHIP_STYLE)
        self.setFixedHeight(28)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        row = QHBoxLayout(self)
        row.setContentsMargins(8, 2, 4, 2)
        row.setSpacing(4)

        lbl = QLabel(label)
        lbl.setStyleSheet(CHIP_LABEL_STYLE)
        row.addWidget(lbl)

        rm_btn = QPushButton("×")
        rm_btn.setFixedSize(18, 18)
        rm_btn.setCursor(Qt.PointingHandCursor)
        rm_btn.setStyleSheet(CHIP_REMOVE_STYLE)
        rm_btn.clicked.connect(lambda: self.removed.emit(self._room_key))
        row.addWidget(rm_btn)


# ---------------------------------------------------------------------------
# EditExamDialog
# ---------------------------------------------------------------------------

class EditExamDialog(QDialog):
    """
    Floating dialog for editing a single exam's date, time slot, and rooms.

    Signals:
        exam_saved(dict): emitted after a successful save; carries the
            updated exam-row dict (same shape as get_period_schedule rows).
    """

    exam_saved = pyqtSignal(dict)

    def __init__(
        self,
        exam: dict,
        period_id: str,
        schedule_index: int,
        service,
        program_names: dict[str, str] | None = None,
        anchor_pos: QPoint | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._exam          = exam
        self._period_id     = period_id
        self._schedule_index = schedule_index
        self._service       = service
        self._program_names = program_names or {}

        # Working copies
        self._selected_date:     date_type         = self._parse_date(exam.get("exam_date"))
        self._selected_slot:     str | None        = exam.get("time_slot")
        self._assigned_rooms:    list[dict]        = []   # {room_key, room_id, building}
        self._all_rooms:         list[dict]        = []   # full availability list
        self._room_scheduling:   bool              = False

        self._build_ui()
        self._load_room_data()

        QTimer.singleShot(0, lambda: QApplication.instance().installEventFilter(self))
        QTimer.singleShot(0, self._center_on_screen)

    # ------------------------------------------------------------------
    # Parse helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_date(value) -> date_type:
        if isinstance(value, date_type):
            return value
        try:
            from datetime import date as dt
            return dt.fromisoformat(str(value))
        except Exception:
            return date_type.today()

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(False)
        self.setMinimumWidth(EDIT_DIALOG_MIN_WIDTH)
        self.setMinimumHeight(EDIT_DIALOG_MIN_HEIGHT)
        self.setMaximumWidth(EDIT_DIALOG_MAX_WIDTH)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._card = QFrame()
        self._card.setObjectName("editExamCard")
        self._card.setStyleSheet(CARD_STYLE)

        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(12)

        # Header row
        card_layout.addLayout(self._build_header())

        # Course info
        card_layout.addWidget(self._build_course_info())

        # Separator
        card_layout.addWidget(self._separator())

        # Reschedule section
        card_layout.addLayout(self._build_reschedule_section())

        # Room assignment section (placeholder — populated after checking service)
        self._room_section = QWidget()
        self._room_section.setVisible(False)
        room_layout = QVBoxLayout(self._room_section)
        room_layout.setContentsMargins(0, 0, 0, 0)
        room_layout.setSpacing(8)
        room_layout.addWidget(self._separator())
        room_layout.addLayout(self._build_room_section())
        card_layout.addWidget(self._room_section)

        # Edit mode notice
        notice = QLabel(
            "Edit mode is active. Changes will be validated for conflicts "
            "and constraints before saving."
        )
        notice.setWordWrap(True)
        notice.setStyleSheet(NOTICE_STYLE)
        card_layout.addWidget(notice)

        # Error banner (hidden by default)
        self._error_label = QLabel()
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet(
            "background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA;"
            " border-radius: 8px; padding: 8px 12px; font-size: 13px;"
        )
        self._error_label.setVisible(False)
        card_layout.addWidget(self._error_label)

        # Footer
        card_layout.addLayout(self._build_footer())

        outer.addWidget(self._card)

    def _separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(SEPARATOR_STYLE)
        return sep

    # ── Header ──────────────────────────────────────────────────────

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)

        course_num  = str(self._exam.get("course_number", ""))
        course_name = str(self._exam.get("course_name", ""))
        title_text  = f"Edit Exam – {course_num} {course_name}".strip(" –")
        title = QLabel(title_text)
        title.setStyleSheet(DIALOG_TITLE_STYLE)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(CLOSE_BTN_STYLE)
        close_btn.clicked.connect(self.close)

        row.addWidget(title)
        row.addStretch()
        row.addWidget(close_btn)
        return row

    # ── Course info ──────────────────────────────────────────────────

    def _build_course_info(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        elective = _is_elective(self._exam)

        # ● time  [Badge]
        time_row = QHBoxLayout()
        time_row.setSpacing(8)

        dot = QLabel("●")
        dot.setStyleSheet(TIME_DOT_STYLE)

        slot_str = self._exam.get("time_slot")
        time_lbl = QLabel(_slot_label(slot_str))
        time_lbl.setStyleSheet(COURSE_TIME_STYLE)

        badge = QLabel("Elective" if elective else "Required")
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            TYPE_BADGE_ELECTIVE_STYLE if elective else TYPE_BADGE_REQUIRED_STYLE
        )

        time_row.addWidget(dot)
        time_row.addWidget(time_lbl)
        time_row.addStretch()
        time_row.addWidget(badge)
        layout.addLayout(time_row)

        # Course name  [View in Day btn]
        name_row = QHBoxLayout()
        name_row.setSpacing(8)

        name_lbl = QLabel(str(self._exam.get("course_name", "—")))
        name_lbl.setStyleSheet(COURSE_NAME_STYLE)

        view_btn = QPushButton("View in Day")
        view_btn.setCursor(Qt.PointingHandCursor)
        view_btn.setStyleSheet(VIEW_IN_DAY_BTN_STYLE)
        view_btn.clicked.connect(self.close)   # closes dialog; output screen still shows day

        name_row.addWidget(name_lbl)
        name_row.addStretch()
        name_row.addWidget(view_btn)
        layout.addLayout(name_row)

        # Programs
        programs = list(self._exam.get("programs") or [])
        program_labels = [
            self._program_names.get(str(p), str(p)) for p in programs
        ]
        programs_str = ", ".join(program_labels) if program_labels else "—"
        prog_lbl = QLabel(f"Programs: {programs_str}")
        prog_lbl.setStyleSheet(COURSE_META_STYLE)
        layout.addWidget(prog_lbl)

        # Current rooms + capacity (if any)
        rooms_display = self._exam.get("rooms_display", [])
        if rooms_display:
            ids = []
            for rd in rooms_display:
                # Format: "• Building B - Room 101 (80 seats)"
                if "Room " in rd and "Building" in rd:
                    building = rd.split("Building ")[-1].split(" -")[0]
                    room_id  = rd.split("Room ")[-1].split(" ")[0]
                    ids.append(f"{room_id} (Building {building})")
                elif "Room " in rd:
                    ids.append(rd.split("Room ")[-1].split(" ")[0])
            rooms_str = ", ".join(ids) if ids else "—"
            rooms_lbl = QLabel(f"Current Rooms: {rooms_str}")
            rooms_lbl.setStyleSheet(COURSE_META_STYLE)
            layout.addWidget(rooms_lbl)

            num_stu = int(self._exam.get("num_students") or 0)
            total   = int(self._exam.get("total_capacity") or 0)
            if num_stu or total:
                cap_lbl = QLabel(f"Capacity: {total} seats for {num_stu} students")
                cap_lbl.setStyleSheet(COURSE_META_STYLE)
                layout.addWidget(cap_lbl)

        return w

    # ── Reschedule section ────────────────────────────────────────────

    def _build_reschedule_section(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(8)

        title = QLabel("Reschedule Exam")
        title.setStyleSheet(SECTION_TITLE_STYLE)
        layout.addWidget(title)

        fields_row = QHBoxLayout()
        fields_row.setSpacing(12)

        # Date field
        date_col = QVBoxLayout()
        date_col.setSpacing(4)
        date_lbl = QLabel("Date")
        date_lbl.setStyleSheet(FIELD_LABEL_STYLE)
        self._date_edit = QDateEdit()
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDisplayFormat("dd/MM/yyyy")
        self._date_edit.setStyleSheet(DATE_EDIT_STYLE)
        qdate = QDate(
            self._selected_date.year,
            self._selected_date.month,
            self._selected_date.day,
        )
        self._date_edit.setDate(qdate)
        self._date_edit.dateChanged.connect(self._on_date_changed)
        date_col.addWidget(date_lbl)
        date_col.addWidget(self._date_edit)

        # Time slot field
        slot_col = QVBoxLayout()
        slot_col.setSpacing(4)
        slot_lbl = QLabel("Time Slot")
        slot_lbl.setStyleSheet(FIELD_LABEL_STYLE)
        self._slot_combo = QComboBox()
        self._slot_combo.setStyleSheet(COMBO_STYLE)
        for display in _TIME_SLOT_DISPLAY.values():
            self._slot_combo.addItem(display)
        # Pre-select current slot
        if self._selected_slot:
            label = _slot_label(self._selected_slot)
            idx = self._slot_combo.findText(label)
            if idx >= 0:
                self._slot_combo.setCurrentIndex(idx)
        self._slot_combo.currentTextChanged.connect(self._on_slot_changed)
        slot_col.addWidget(slot_lbl)
        slot_col.addWidget(self._slot_combo)

        fields_row.addLayout(date_col, stretch=1)
        fields_row.addLayout(slot_col, stretch=1)
        layout.addLayout(fields_row)
        return layout

    # ── Room assignment section ───────────────────────────────────────

    def _build_room_section(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(8)

        title = QLabel("Room Assignment")
        title.setStyleSheet(SECTION_TITLE_STYLE)
        layout.addWidget(title)

        # "Assigned Rooms (N)" + Clear All
        chips_header = QHBoxLayout()
        self._assigned_label = QLabel("Assigned Rooms (0)")
        self._assigned_label.setStyleSheet(ASSIGNED_ROOMS_LABEL_STYLE)
        clear_btn = QPushButton("Clear All")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(CLEAR_ALL_BTN_STYLE)
        clear_btn.clicked.connect(self._on_clear_all)
        chips_header.addWidget(self._assigned_label)
        chips_header.addStretch()
        chips_header.addWidget(clear_btn)
        layout.addLayout(chips_header)

        # Chips row (scrollable)
        self._chips_scroll = QScrollArea()
        self._chips_scroll.setMaximumHeight(40)
        self._chips_scroll.setWidgetResizable(True)
        self._chips_scroll.setFrameShape(QFrame.NoFrame)
        self._chips_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._chips_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._chips_scroll.setStyleSheet("background: transparent;")

        self._chips_container = QWidget()
        self._chips_container.setStyleSheet("background: transparent;")
        self._chips_layout = QHBoxLayout(self._chips_container)
        self._chips_layout.setContentsMargins(0, 0, 0, 0)
        self._chips_layout.setSpacing(6)
        self._chips_layout.addStretch()
        self._chips_scroll.setWidget(self._chips_container)
        layout.addWidget(self._chips_scroll)

        # Capacity summary: "X / Y seats  (N rooms)"
        self._capacity_summary = QLabel()
        self._capacity_summary.setStyleSheet(
            "color: #64748B; font-size: 12px; background: transparent;"
        )
        layout.addWidget(self._capacity_summary)

        # Available rooms header
        avail_lbl = QLabel("Available Rooms")
        avail_lbl.setStyleSheet(AVAIL_ROOMS_LABEL_STYLE)
        layout.addWidget(avail_lbl)

        # Search + filter row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search rooms...")
        self._search_edit.setStyleSheet(SEARCH_STYLE)
        self._search_edit.textChanged.connect(self._apply_table_filter)

        self._building_combo = QComboBox()
        self._building_combo.setStyleSheet(FILTER_COMBO_STYLE)
        self._building_combo.addItem("All Buildings")
        self._building_combo.currentTextChanged.connect(self._apply_table_filter)

        self._capacity_combo = QComboBox()
        self._capacity_combo.setStyleSheet(FILTER_COMBO_STYLE)
        for label in ["Capacity: Any", "< 50", "50–100", "100–200", "200+"]:
            self._capacity_combo.addItem(label)
        self._capacity_combo.currentTextChanged.connect(self._apply_table_filter)

        filter_row.addWidget(self._search_edit, stretch=2)
        filter_row.addWidget(self._building_combo, stretch=1)
        filter_row.addWidget(self._capacity_combo, stretch=1)
        layout.addLayout(filter_row)

        # Room table
        self._room_table = QTableWidget(0, 5)
        self._room_table.setHorizontalHeaderLabels(
            ["Room", "Building", "Capacity", "Available Seats", "Action"]
        )
        self._room_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._room_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._room_table.verticalHeader().setVisible(False)
        self._room_table.setSelectionMode(QTableWidget.NoSelection)
        self._room_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._room_table.setStyleSheet(TABLE_STYLE)
        self._room_table.setMaximumHeight(280)
        self._room_table.setShowGrid(False)
        layout.addWidget(self._room_table)

        # Capacity hint
        self._slot_hint = QLabel(
            f"ⓘ Capacity shown is for the selected time slot "
            f"({_slot_label(self._selected_slot)})"
        )
        self._slot_hint.setStyleSheet(CAPACITY_HINT_STYLE)
        layout.addWidget(self._slot_hint)

        return layout

    # ── Footer ───────────────────────────────────────────────────────

    def _build_footer(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(CANCEL_BTN_STYLE)
        cancel_btn.clicked.connect(self.close)

        self._save_btn = QPushButton("Save Changes")
        self._save_btn.setCursor(Qt.PointingHandCursor)
        self._save_btn.setStyleSheet(SAVE_BTN_STYLE)
        self._save_btn.clicked.connect(self._on_save)

        row.addStretch()
        row.addWidget(cancel_btn)
        row.addWidget(self._save_btn)
        return row

    # ------------------------------------------------------------------
    # Room data loading
    # ------------------------------------------------------------------

    def _load_room_data(self) -> None:
        """Load room availability from the service and populate UI."""
        try:
            settings = self._service.get_constraint_settings()
            self._room_scheduling = getattr(settings, "room_scheduling_enabled", False)
        except Exception:
            self._room_scheduling = False

        if not self._room_scheduling:
            return

        self._room_section.setVisible(True)

        # Initialise assigned rooms from the exam's current room data
        rooms_display = self._exam.get("rooms_display", [])
        room_ids_raw  = self._exam.get("room_ids", [])

        for key in room_ids_raw:
            # key format: "building:room_id"
            parts = key.split(":", 1)
            if len(parts) == 2:
                building, room_id = parts
                self._assigned_rooms.append({
                    "room_key": key,
                    "room_id":  room_id,
                    "building": building,
                })

        self._refresh_room_availability()

    def _refresh_room_availability(self) -> None:
        """Re-query availability for the current date + slot, then redraw."""
        try:
            course_number = str(self._exam.get("course_number", ""))
            self._all_rooms = self._service.get_room_availability(
                period_id=self._period_id,
                index=self._schedule_index,
                target_date=self._selected_date,
                time_slot=self._selected_slot or "",
                exclude_course_number=course_number,
            )
        except Exception:
            self._all_rooms = []

        # Sync assigned list with room data
        available_keys = {r["room_key"] for r in self._all_rooms}
        self._assigned_rooms = [
            r for r in self._assigned_rooms if r["room_key"] in available_keys
        ]

        # Update building filter
        buildings = sorted({r["building"] for r in self._all_rooms})
        current = self._building_combo.currentText()
        self._building_combo.blockSignals(True)
        self._building_combo.clear()
        self._building_combo.addItem("All Buildings")
        for b in buildings:
            self._building_combo.addItem(b)
        idx = self._building_combo.findText(current)
        self._building_combo.setCurrentIndex(max(0, idx))
        self._building_combo.blockSignals(False)

        self._refresh_chips()
        self._apply_table_filter()
        self._update_slot_hint()

    # ------------------------------------------------------------------
    # Chip rendering
    # ------------------------------------------------------------------

    def _refresh_chips(self) -> None:
        # Remove existing chips (keep stretch at end)
        while self._chips_layout.count() > 1:
            item = self._chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for room_info in self._assigned_rooms:
            label = (
                f"{room_info['room_id']} ({room_info['building']})"
                if room_info.get("building")
                else room_info["room_id"]
            )
            chip = _RoomChip(
                room_key=room_info["room_key"],
                label=label,
            )
            chip.removed.connect(self._on_chip_removed)
            self._chips_layout.insertWidget(self._chips_layout.count() - 1, chip)

        n = len(self._assigned_rooms)
        self._assigned_label.setText(f"Assigned Rooms ({n})")
        self._update_capacity_summary()

    def _update_capacity_summary(self) -> None:
        if not hasattr(self, "_capacity_summary"):
            return
        num_students = int(self._exam.get("num_students") or 0)
        n = len(self._assigned_rooms)

        if n == 0:
            if num_students:
                self._capacity_summary.setText(
                    f"No rooms selected — need capacity for {num_students} students."
                )
                self._capacity_summary.setStyleSheet(
                    "color: #DC2626; font-size: 12px; background: transparent;"
                )
            else:
                self._capacity_summary.setText("")
            return

        # Sum capacity of currently assigned rooms using _all_rooms data
        rooms_by_key = {r["room_key"]: r for r in self._all_rooms}
        total_cap = sum(
            rooms_by_key[r["room_key"]]["capacity"]
            for r in self._assigned_rooms
            if r["room_key"] in rooms_by_key
        )

        if num_students:
            status = "✓" if total_cap >= num_students else "✗ not enough"
            color  = "#16A34A" if total_cap >= num_students else "#DC2626"
            text   = (
                f"Selected capacity: {total_cap} / {num_students} seats  "
                f"({n} {'room' if n == 1 else 'rooms'})  {status}"
            )
        else:
            color = "#64748B"
            text  = f"Selected capacity: {total_cap} seats  ({n} {'room' if n == 1 else 'rooms'})"

        self._capacity_summary.setText(text)
        self._capacity_summary.setStyleSheet(
            f"color: {color}; font-size: 12px; background: transparent;"
        )

    # ------------------------------------------------------------------
    # Table rendering
    # ------------------------------------------------------------------

    def _apply_table_filter(self) -> None:
        search     = self._search_edit.text().strip().lower() if hasattr(self, "_search_edit") else ""
        building_f = self._building_combo.currentText()        if hasattr(self, "_building_combo") else "All Buildings"
        cap_f      = self._capacity_combo.currentText()        if hasattr(self, "_capacity_combo") else "Capacity: Any"

        assigned_keys = {r["room_key"] for r in self._assigned_rooms}

        filtered = []
        for room in self._all_rooms:
            if search and search not in room["room_id"].lower() and search not in room["building"].lower():
                continue
            if building_f != "All Buildings" and room["building"] != building_f:
                continue
            cap = room["capacity"]
            if cap_f == "< 50" and cap >= 50:
                continue
            if cap_f == "50–100" and not (50 <= cap <= 100):
                continue
            if cap_f == "100–200" and not (100 < cap <= 200):
                continue
            if cap_f == "200+" and cap <= 200:
                continue
            filtered.append(room)

        self._room_table.setRowCount(len(filtered))
        for row_idx, room in enumerate(filtered):
            key        = room["room_key"]
            is_assigned = key in assigned_keys

            self._room_table.setItem(row_idx, 0, self._cell(room["room_id"]))
            self._room_table.setItem(row_idx, 1, self._cell(room["building"]))
            self._room_table.setItem(row_idx, 2, self._cell(str(room["capacity"])))
            self._room_table.setItem(row_idx, 3, self._cell(str(room["free_seats"])))

            is_full = (
                not is_assigned
                and int(room.get("free_seats", 0)) < int(room.get("capacity", 0))
            )

            if is_assigned:
                btn = QPushButton("Assigned")
                btn.setStyleSheet(ASSIGNED_BTN_STYLE)
                btn.setEnabled(False)
            elif is_full:
                btn = QPushButton("Occupied")
                btn.setStyleSheet(
                    "QPushButton { background: #FEF2F2; color: #DC2626;"
                    " border: 1.5px solid #FECACA; border-radius: 6px;"
                    " padding: 3px 10px; font-size: 12px; font-weight: 600; }"
                )
                btn.clicked.connect(
                    lambda _, r=room: self._show_error(
                        f"Room {r['room_id']} ({r['building']}) is fully occupied "
                        f"in this time slot — no seats available."
                    )
                )
            else:
                btn = QPushButton("Assign")
                btn.setStyleSheet(ASSIGN_BTN_STYLE)
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda _, r=room: self._on_assign_room(r))

            self._room_table.setCellWidget(row_idx, 4, btn)

        self._room_table.resizeRowsToContents()

    @staticmethod
    def _cell(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def _update_slot_hint(self) -> None:
        if hasattr(self, "_slot_hint"):
            self._slot_hint.setText(
                f"ⓘ Capacity shown is for the selected time slot "
                f"({_slot_label(self._selected_slot)})"
            )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_date_changed(self, qdate: QDate) -> None:
        self._selected_date = date_type(qdate.year(), qdate.month(), qdate.day())
        if self._room_scheduling:
            self._refresh_room_availability()
        self._validate_current_date()

    def _validate_current_date(self) -> bool:
        """Run validate_manual_move for the currently selected date and show
        inline errors immediately. Returns True if the date is valid."""
        try:
            # Build a snapshot of rows from the service so the validator has
            # the full context (including other exams for collision checks).
            rows = self._service.get_period_schedule(
                self._period_id, self._schedule_index
            ) or []
            errors = self._service.validate_manual_move(
                self._period_id, rows, self._exam, self._selected_date
            )
        except Exception:
            errors = []

        if errors:
            reasons = "\n".join(f"• {e['reason']}" for e in errors)
            self._show_error(reasons)
            self._save_btn.setEnabled(False)
            return False

        self._hide_error()
        self._save_btn.setEnabled(True)
        return True

    def _on_slot_changed(self, display: str) -> None:
        self._selected_slot = _DISPLAY_TO_SLOT.get(display, display)
        if self._room_scheduling:
            self._refresh_room_availability()
        self._hide_error()

    def _on_assign_room(self, room: dict) -> None:
        key = room["room_key"]
        if any(r["room_key"] == key for r in self._assigned_rooms):
            return
        self._assigned_rooms.append({
            "room_key": key,
            "room_id":  room["room_id"],
            "building": room["building"],
        })
        self._refresh_chips()
        self._apply_table_filter()
        self._hide_error()

    def _on_chip_removed(self, room_key: str) -> None:
        self._assigned_rooms = [r for r in self._assigned_rooms if r["room_key"] != room_key]
        self._refresh_chips()
        self._apply_table_filter()

    def _on_clear_all(self) -> None:
        self._assigned_rooms.clear()
        self._refresh_chips()
        self._apply_table_filter()

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        self._hide_error()

        # Re-validate date before writing to disk
        if not self._validate_current_date():
            return

        if self._room_scheduling:
            errors = self._validate_capacity()
            if errors:
                self._show_error(errors[0])
                return

        new_room_keys = [r["room_key"] for r in self._assigned_rooms]
        updated = dict(self._exam)
        updated["exam_date"] = self._selected_date
        if self._selected_slot is not None:
            updated["time_slot"] = self._selected_slot
        updated["room_ids"] = new_room_keys

        self.exam_saved.emit(updated)
        self.close()

    def _validate_capacity(self) -> list[str]:
        num_students = int(self._exam.get("num_students") or 0)
        if num_students == 0:
            return []
        selected_keys = {x["room_key"] for x in self._assigned_rooms}
        total_cap = sum(
            r.get("free_seats", 0)
            for r in self._all_rooms
            if r["room_key"] in selected_keys
        )
        if total_cap < num_students:
            course_name = self._exam.get("course_name", str(self._exam.get("course_number", "")))
            return [
                f"{course_name} has {num_students} students but selected rooms "
                f"only fit {total_cap}. Please assign more rooms."
            ]
        return []

    # ------------------------------------------------------------------
    # Error banner
    # ------------------------------------------------------------------

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.setVisible(True)

    def _hide_error(self) -> None:
        self._error_label.setVisible(False)

    # ------------------------------------------------------------------
    # showEvent / close / outside-click
    # ------------------------------------------------------------------

    def showEvent(self, event) -> None:
        super().showEvent(event)

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        geo    = self.frameGeometry()
        # Place on the RIGHT half so the day-list panel can sit to the left.
        x = screen.left() + screen.width() // 2 + (screen.width() // 2 - geo.width()) // 2
        y = screen.top()  + (screen.height() - geo.height()) // 2
        x = max(screen.left(), min(x, screen.right()  - geo.width()))
        y = max(screen.top(),  min(y, screen.bottom() - geo.height()))
        self.move(x, y)

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.MouseButtonPress:
            if not self.geometry().contains(event.globalPos()):
                self.close()
                return False
        return super().eventFilter(obj, event)

    def closeEvent(self, event) -> None:
        QApplication.instance().removeEventFilter(self)
        super().closeEvent(event)
