"""
ranking_config_widget.py
-------------------------
Drag-and-drop metric ranking sub-component for schedule output sorting.
Only checked rows participate in sorting.  get_sort_order() returns the keys
of checked rows in their current visual order (top = highest priority).
Unchecked rows are excluded from the result.

Numbers update automatically after every drag or checkbox toggle.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QAbstractItemView, QCheckBox,
    QPushButton,
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QFont

# Qt's "unbounded width" sentinel — used to release a temporary fixed width.
_QWIDGETSIZE_MAX = 16777215

from src.styles import output_sorting_panel_style as _style


# Maps each metric key to the full sentence shown inside its list row.
_METRIC_TITLES: dict[str, str] = {
    "min_days_required": "Minimum gap between mandatory exams",
    "avg_days_all":      "Average gap between consecutive exams",
    "elective_conflicts": "Elective exam conflicts",
    "span_required":     "Span of mandatory exams",
    "max_exams_per_day": "Peak exams per day",
    "avg_room_distance": "Average room distance",
}

_METRIC_DESCRIPTIONS: dict[str, str] = {
    "min_days_required": (
        "Same program and year - schedules with a larger minimum gap are ranked first."
    ),
    "avg_days_all": (
        "Mandatory and elective exams, same program and year - wider average spacing ranked first."
    ),
    "elective_conflicts": (
        "Same program - schedules with fewer same-day elective clashes are ranked first."
    ),
    "span_required": (
        "Same program, year and moed - schedules where first and last mandatory exams "
        "are furthest apart are ranked first."
    ),
    "max_exams_per_day": (
        "Schedules with fewer exams on the busiest day are ranked first."
    ),
    "avg_room_distance": (
        "Room scheduling mode - schedules with lower room/building spread are ranked first."
    ),
}

# The visual top-to-bottom order of rows when the widget first appears.
_DEFAULT_ORDER: list[str] = [
    "min_days_required",
    "avg_days_all",
    "elective_conflicts",
    "span_required",
    "max_exams_per_day",
    "avg_room_distance",
]

# Empty set — all rows start unchecked so the user explicitly picks criteria.
_DEFAULT_CHECKED: set[str] = set()


class _RowWidget(QWidget):
    """One row inside the list: drag-handle | badge | title+description | checkbox."""

    def __init__(self, key: str, title: str, description: str, parent=None):
        super().__init__(parent)

        self.key = key

        outer = QHBoxLayout(self)
        outer.setContentsMargins(_style.ROW_MARGIN_H, _style.ROW_MARGIN_V,
                                 _style.ROW_MARGIN_H, _style.ROW_MARGIN_V)
        outer.setSpacing(_style.ROW_SPACING)

        # ── Drag handle ───────────────────────────────────────────────────
        handle = QLabel("⠿")
        handle.setStyleSheet(_style.DRAG_HANDLE)
        handle.setFixedWidth(_style.HANDLE_WIDTH)
        outer.addWidget(handle)

        # ── Priority badge ────────────────────────────────────────────────
        self.badge = QLabel("1")
        self.badge.setFixedSize(_style.BADGE_SIZE, _style.BADGE_SIZE)
        self.badge.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setBold(True)
        font.setPointSize(_style.BADGE_FONT_PT)
        self.badge.setFont(font)
        self._set_badge_active(True)
        outer.addWidget(self.badge)

        # ── Text block: title (large) + description (small) ───────────────
        text_block = QVBoxLayout()
        text_block.setSpacing(_style.TEXT_BLOCK_SPACING)

        title_lbl = QLabel(title)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(_style.ROW_TITLE_LABEL)
        text_block.addWidget(title_lbl)

        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(_style.DESCRIPTION_LABEL)
        text_block.addWidget(desc_lbl)

        outer.addLayout(text_block, stretch=1)

        # ── Checkbox ──────────────────────────────────────────────────────
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.setStyleSheet(_style.CHECKBOX)
        outer.addWidget(self.checkbox)

    def set_badge_number(self, number: int | None) -> None:
        """Update the badge to show a priority number or go grey/empty.

        Called by RankingConfigWidget._refresh_badges() after every
        drag or checkbox toggle.
        number=None  → row is unchecked, badge becomes grey and blank.
        number=1,2,… → row is checked, badge shows the priority rank.
        """
        if number is None:
            self.badge.setText("")          # remove the number text
            self._set_badge_active(False)   # switch to grey style
        else:
            self.badge.setText(str(number)) # show the rank number
            self._set_badge_active(True)    # switch to blue style

    def _set_badge_active(self, active: bool) -> None:
        # Swap between the blue (active) and grey (inactive) stylesheet string.
        self.badge.setStyleSheet(
            _style.BADGE_ACTIVE if active else _style.BADGE_INACTIVE
        )


class RankingConfigWidget(QWidget):
    """Right panel of SettingsScreen — checkbox + drag to set metric priority."""

    sort_order_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._list: QListWidget   # declared here so type checkers know the attribute
        # Checked state tracked independently of the row widgets. A drag-reorder
        # destroys the moved row's widget (Qt InternalMove limitation), so we
        # must remember which keys are checked outside the widgets themselves.
        self._checked: set[str] = set(_DEFAULT_CHECKED)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setObjectName("OutputSortingPanel")
        self.setFixedWidth(_style.PANEL_WIDTH)
        self.setStyleSheet(_style.PANEL_WIDGET)

        # QVBoxLayout stacks children top-to-bottom.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            _style.PANEL_MARGIN,
            _style.PANEL_MARGIN,
            _style.PANEL_MARGIN,
            _style.PANEL_MARGIN,
        )
        layout.setSpacing(_style.PANEL_SPACING)

        # Section title shown above the list.
        title = QLabel("Sorting Preferences")
        title.setStyleSheet(_style.TITLE_LABEL)
        layout.addWidget(title)

        # Instructional subtitle below the title.
        subtitle = QLabel("Select criteria and drag to set priority")
        subtitle.setStyleSheet(_style.SUBTITLE_LABEL)
        layout.addWidget(subtitle)

        # QListWidget is the scrollable container that holds all metric rows.
        self._list = QListWidget()

        # InternalMove: rows can be dragged and dropped within this same list
        # to reorder them.  Qt handles the drag animation automatically.
        self._list.setDragDropMode(QAbstractItemView.InternalMove)

        # MoveAction: dragging a row moves it (doesn't copy it).
        self._list.setDefaultDropAction(Qt.MoveAction)

        # SingleSelection: only one row can be highlighted at a time.
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)

        # 4-pixel gap between cards so they look separated.
        self._list.setSpacing(4)

        self._list.setStyleSheet(_style.LIST_WIDGET)

        # Fill the list with the five metric rows in the default order.
        self._populate_list(_DEFAULT_ORDER, _DEFAULT_CHECKED)

        # rowsMoved fires after every successful drag-drop reorder. Qt destroys
        # the moved row's item widget during an InternalMove, so we rebuild all
        # rows here instead of only refreshing badges.
        self._list.model().rowsMoved.connect(self._on_rows_moved)

        # stretch=1 makes the list expand to fill all remaining vertical space.
        layout.addWidget(self._list, stretch=1)

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setStyleSheet(_style.APPLY_BUTTON)
        self.apply_btn.clicked.connect(self._emit_sort_order)
        layout.addWidget(self.apply_btn)

    def _populate_list(self, order: list[str], checked: set[str]) -> None:
        """Clear the list and rebuild one _RowWidget per key in order."""
        self._list.clear()
        # This call is the source of truth for the checked set going forward.
        self._checked = set(checked)
        for key in order:
            title = _METRIC_TITLES.get(key, key)
            desc = _METRIC_DESCRIPTIONS.get(key, "")

            # Build the visible row widget (handle + badge + title + desc + checkbox).
            row_widget = _RowWidget(key, title, desc)
            row_widget.checkbox.setChecked(key in checked)

            # Keep the independent checked set in sync, then recalc badges.
            row_widget.checkbox.toggled.connect(
                lambda is_on, k=key: self._on_toggle(k, is_on)
            )

            # QListWidgetItem is the internal list entry that Qt manages.
            # It is invisible — the _RowWidget is placed on top of it.
            item = QListWidgetItem(self._list)

            # Store the metric key as hidden data on the item so we can
            # read it back in get_sort_order() without parsing the label text.
            item.setData(Qt.UserRole, key)

            # ItemIsEnabled   — row responds to clicks
            # ItemIsSelectable — row can be highlighted
            # ItemIsDragEnabled — row can be picked up and moved
            item.setFlags(
                Qt.ItemIsEnabled
                | Qt.ItemIsSelectable
                | Qt.ItemIsDragEnabled
            )

            # Tell the list how tall this item should be so the custom widget fits.
            item.setSizeHint(row_widget.sizeHint())

            self._list.addItem(item)

            # Attach the visible _RowWidget on top of the invisible item.
            self._list.setItemWidget(item, row_widget)

        # Set correct badge numbers for the initial state.
        self._refresh_badges()

        # Item size hints were taken before the rows knew their real width, so
        # recompute them now that every row is in the list.
        self._sync_row_heights()

    def _sync_row_heights(self) -> None:
        """Resize each item to fit its word-wrapped text at the list's real width.

        QListWidget fixes an item's size hint when the row is added — before the
        row knows how wide it will actually be on screen.  Word-wrapped
        descriptions then report a too-small height, so the lower rows get
        clipped, and a clipped row can repaint blank after a scroll (only the
        checkbox survives — exactly the reported bug).

        For each row we temporarily pin it to the real available width, measure
        the height its wrapped text needs, then release the width so the view
        can still stretch the row to fill the item.
        """
        avail = self._list.viewport().width() - 2 * self._list.spacing() - 2
        if avail <= 0:
            return
        for i in range(self._list.count()):
            item = self._list.item(i)
            widget = self._list.itemWidget(item)
            if widget is None:
                continue
            widget.setFixedWidth(avail)
            widget.adjustSize()
            height = widget.sizeHint().height()
            # Release the temporary width pin (0 .. unbounded) so the view may
            # resize the row to the full item width on layout.
            widget.setMinimumWidth(0)
            widget.setMaximumWidth(_QWIDGETSIZE_MAX)
            item.setSizeHint(QSize(avail, height))

    def resizeEvent(self, event) -> None:
        # The panel width is fixed, but the viewport width is only known once
        # the widget is laid out — recompute heights whenever it changes.
        super().resizeEvent(event)
        self._sync_row_heights()

    def showEvent(self, event) -> None:
        # First reliable point where the viewport has its real width.
        super().showEvent(event)
        self._sync_row_heights()

    def _refresh_badges(self) -> None:
        """Walk the list top-to-bottom and assign sequential numbers to checked rows.

        Called after every drag or checkbox toggle so the displayed numbers
        always match the current visual order.
        """
        counter = 1
        for i in range(self._list.count()):
            item = self._list.item(i)
            widget: _RowWidget = self._list.itemWidget(item)
            if widget is None:
                continue
            if widget.checkbox.isChecked():
                widget.set_badge_number(counter)  # blue badge with rank number
                counter += 1
            else:
                widget.set_badge_number(None)     # grey empty badge

    def _on_toggle(self, key: str, is_on: bool) -> None:
        """Mirror a checkbox change into the independent checked set, then renumber."""
        if is_on:
            self._checked.add(key)
        else:
            self._checked.discard(key)
        self._refresh_badges()

    def _current_order(self) -> list[str]:
        """Read the metric keys top-to-bottom from the items' stored data.

        The item data survives a drag-reorder even though the row widget does
        not, so this is the reliable source for the post-drag order.
        """
        return [
            self._list.item(i).data(Qt.UserRole)
            for i in range(self._list.count())
        ]

    def _on_rows_moved(self, *_args) -> None:
        """Rebuild every row after a drag so the moved (now-blank) row reappears.

        Qt's InternalMove physically re-inserts the dragged item and discards
        the custom widget attached with setItemWidget, leaving an empty card.
        We capture the new order from the surviving item data and the checked
        state from self._checked, then repopulate from scratch. Deferred with a
        0 ms timer so the rebuild runs after the drag event has fully settled.
        """
        order = self._current_order()
        checked = set(self._checked)
        QTimer.singleShot(0, lambda: self._populate_list(order, checked))

    def _emit_sort_order(self) -> None:
        """Emit the selected sort order only when the user applies it."""
        self.sort_order_changed.emit(self.get_sort_order())


    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_sort_order(self) -> list[str]:
        """Return metric keys for checked rows in top-to-bottom visual order.

        Unchecked rows are excluded.  The result is ready to pass directly
        to WindowState.set_sort() or RankingQueryEngine.fetch_window().

        Example (rows 1 and 3 unchecked):
            ["min_days_required", "span_required", "max_exams_per_day"]
        """
        result = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            widget: _RowWidget = self._list.itemWidget(item)
            if widget is not None and widget.checkbox.isChecked():
                # Read the metric key stored as hidden data on the item.
                result.append(item.data(Qt.UserRole))
        return result

    def set_sort_order(self, order: list[str], checked: set[str] | None = None) -> None:
        """Repopulate the list from an external key sequence.

        order   — top-to-bottom sequence of metric keys (e.g. loaded from DB).
        checked — which keys should start checked; omit to check all of them.
        Unknown keys are silently ignored so stale saved settings never crash.
        """
        # Drop any key that isn't in our descriptions dict.
        valid = [k for k in order if k in _METRIC_DESCRIPTIONS]

        # Append any known metric not present in the supplied order so every
        # metric always remains visible in the UI (the BLOCK fix).
        full_order = valid + [k for k in _DEFAULT_ORDER if k not in valid]

        # If no checked set given, treat the explicitly-ordered keys as checked.
        active = set(valid) if checked is None else (checked & set(full_order))

        self._populate_list(full_order, active)
