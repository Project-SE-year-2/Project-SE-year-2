"""
ranking_config_widget.py
-------------------------
Drag-and-drop metric ranking sub-component for SettingsScreen (EP-112).
Only checked rows participate in sorting.  get_sort_order() returns the keys
of checked rows in their current visual order (top = highest priority).
Unchecked rows are excluded from the result.

Numbers update automatically after every drag or checkbox toggle.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QAbstractItemView, QCheckBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from src.views.settings_screen.styles import ranking_config_widget_style as _style


# Maps each metric key to the full sentence shown inside its list row.
_METRIC_DESCRIPTIONS: dict[str, str] = {
    "min_days_required": (
        "Minimize the minimum gap between two required-course exams "
        "in the same program and same year."
    ),
    "avg_days_all": (
        "Minimize the average gap between required/elective exams "
        "in the same program and same year."
    ),
    "elective_conflicts": (
        "Minimize the number of conflicts between two elective-course "
        "exams in the same program."
    ),
    "span_required": (
        "Minimize the gap between the first required-course exam and "
        "the last required-course exam in a selected program, year and moed."
    ),
    "max_exams_per_day": (
        "Minimize the maximum number of exams scheduled on the same day."
    ),
}

# The visual top-to-bottom order of rows when the widget first appears.
_DEFAULT_ORDER: list[str] = [
    "min_days_required",
    "avg_days_all",
    "elective_conflicts",
    "span_required",
    "max_exams_per_day",
]

# Empty set — all rows start unchecked so the user explicitly picks criteria.
_DEFAULT_CHECKED: set[str] = set()


class _RowWidget(QWidget):
    """One row inside the list: drag-handle | badge | description | checkbox.

    This is a private helper — only RankingConfigWidget creates instances.
    """

    def __init__(self, key: str, description: str, parent=None):
        super().__init__(parent)

        # Remember which metric key this row represents.
        self.key = key

        # QHBoxLayout arranges children left-to-right in a single line.
        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)  # padding inside the row card
        outer.setSpacing(12)                   # gap between each child widget

        # ── Drag handle ──────────────────────────────────────────────────
        # A braille-dots character rendered as a visual grip icon.
        # setFixedWidth keeps it narrow so it doesn't take up space.
        handle = QLabel("⠿")
        handle.setStyleSheet(_style.DRAG_HANDLE)
        handle.setFixedWidth(16)
        outer.addWidget(handle)

        # ── Priority badge ────────────────────────────────────────────────
        # A square QLabel sized to a circle via border-radius in the stylesheet.
        # Shows "1", "2", … when checked; empty and grey when unchecked.
        self.badge = QLabel("1")
        self.badge.setFixedSize(28, 28)          # fixed square so it stays circular
        self.badge.setAlignment(Qt.AlignCenter)  # number centred inside the circle
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        self.badge.setFont(font)
        self._set_badge_active(True)   # start blue (will be overridden by _refresh_badges)
        outer.addWidget(self.badge)

        # ── Description label ─────────────────────────────────────────────
        # stretch=1 tells the layout to give all remaining horizontal space to
        # this widget, pushing the checkbox to the far right.
        desc = QLabel(description)
        desc.setWordWrap(True)   # allow the text to wrap onto multiple lines
        desc.setStyleSheet(_style.DESCRIPTION_LABEL)
        outer.addWidget(desc, stretch=1)

        # ── Checkbox ──────────────────────────────────────────────────────
        # Determines whether this metric is included in the sort order.
        # Starts unchecked; RankingConfigWidget sets the real value after init.
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._list: QListWidget   # declared here so type checkers know the attribute
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # QVBoxLayout stacks children top-to-bottom.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Section title shown above the list.
        title = QLabel("Sort & Prioritize Schedule")
        title.setStyleSheet(_style.TITLE_LABEL)
        layout.addWidget(title)

        # Instructional subtitle below the title.
        subtitle = QLabel("Select and drag to prioritize the sorting methods")
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

        # rowsMoved fires after every successful drag-drop reorder.
        # We reconnect badge numbers so they reflect the new visual position.
        self._list.model().rowsMoved.connect(self._refresh_badges)

        # stretch=1 makes the list expand to fill all remaining vertical space.
        layout.addWidget(self._list, stretch=1)

    def _populate_list(self, order: list[str], checked: set[str]) -> None:
        """Clear the list and rebuild one _RowWidget per key in order."""
        self._list.clear()
        for key in order:
            desc = _METRIC_DESCRIPTIONS.get(key, key)

            # Build the visible row widget (handle + badge + text + checkbox).
            row_widget = _RowWidget(key, desc)
            row_widget.checkbox.setChecked(key in checked)

            # Whenever this row's checkbox is toggled, recalculate all badges.
            row_widget.checkbox.toggled.connect(self._refresh_badges)

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

        # If no checked set given, treat all valid keys as checked.
        active = set(valid) if checked is None else (checked & set(valid))

        self._populate_list(valid, active)
