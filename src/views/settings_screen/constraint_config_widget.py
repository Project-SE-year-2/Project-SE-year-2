"""
constraint_config_widget.py
----------------------------
Form-based sub-component for enabling and configuring scheduling constraints.

Each of the five K-constraints has:
  - A QCheckBox  stored in self._checks[key]  — toggles the rule on/off.
  - A QSpinBox   stored in self._spins[key]   — sets the K parameter value.

When the checkbox is unchecked the paired spinbox is disabled and grayed out.
When it is checked the spinbox becomes interactive again.

Keys used in both dicts (match ConstraintSettings field prefixes):
  "mandatory_gap", "all_gap", "elective_conflicts", "spread", "daily_cap"

Room scheduling is a separate boolean-only toggle (_room_scheduling_check).
It has no spinbox because it does not take a K parameter - it simply flips
ConstraintSettings.room_scheduling_enabled on or off.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QCheckBox, QSpinBox, QFrame,
)
from PyQt5.QtCore import Qt

from src.models.constraint_settings import ConstraintSettings

# Human-readable label for each constraint key.
_CONSTRAINT_LABELS = {
    "mandatory_gap":       "Mandatory Gap (days)",
    "all_gap":             "All Gap (days)",
    "elective_conflicts":  "Elective Conflicts (max)",
    "spread":              "Spread (min days)",
    "daily_cap":           "Daily Cap (max exams)",
}

_CONSTRAINT_DESCRIPTIONS = {
    "mandatory_gap": "Minimum days between obligatory exams for the same cohort.",
    "all_gap": "Minimum days between any exams (including electives) for the same cohort.",
    "elective_conflicts": "Maximum overlapping elective exams allowed per day for a program.",
    "spread": "Minimum length of the exam period from the first to the last obligatory exam.",
    "daily_cap": "Maximum total exams scheduled across the entire institution on a single day.",
}

# Sensible default K-values shown in the spinbox when the widget first loads.
_DEFAULT_K = {
    "mandatory_gap":      3,
    "all_gap":            3,
    "elective_conflicts": 0,
    "spread":             7,
    "daily_cap":          3,
}

# Lower bound for each spinbox (EP-110 validation rules):
#   elective_conflicts → 0  (zero conflicts is a valid target)
#   all gap/calendar constraints → 0  (a gap of 0 days is meaningless)
_MIN_K = {
    "mandatory_gap":      0,
    "all_gap":            0,
    "elective_conflicts": 0,
    "spread":             0,
    "daily_cap":          0,
}

# Upper bound for each spinbox.
_MAX_K = {
    "mandatory_gap":      30,
    "all_gap":            30,
    "elective_conflicts": 10,
    "spread":             60,
    "daily_cap":          10,
}

# Shared styles reused in both K-constraint rows and the room scheduling row.
_CHECKBOX_STYLE = """
    QCheckBox::indicator {
        width: 24px; height: 24px;
        border-radius: 6px;
        border: 2px solid #94A3B8;
    }
    QCheckBox::indicator:checked {
        background-color: #3B82F6;
        border-color: #3B82F6;
    }
    QCheckBox::indicator:unchecked {
        background-color: #FFFFFF;
    }
    QCheckBox::indicator:unchecked:hover {
        border-color: #64748B;
    }
"""
_ROW_LABEL_STYLE = "color: #0F172A; font-size: 16px; font-weight: 600;"
_ROW_DESC_STYLE  = "color: #64748B; font-size: 13px;"


class ConstraintConfigWidget(QWidget):
    """Left panel of SettingsScreen - one checkbox+spinbox row per K-constraint,
    plus a boolean-only toggle for room scheduling."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Maps constraint key → QCheckBox (for the five K-constraints)
        self._checks: dict[str, QCheckBox] = {}
        # Maps constraint key → QSpinBox (for the five K-constraints)
        self._spins: dict[str, QSpinBox] = {}
        # Standalone boolean toggle for room scheduling - no paired spinbox.
        self._room_scheduling_check: QCheckBox | None = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        title = QLabel("Constraint Settings")
        title.setStyleSheet("font-weight: bold; font-size: 18px; color: #0F172A;")
        layout.addWidget(title)

        layout.addWidget(self._make_divider())

        for key in _CONSTRAINT_LABELS:
            layout.addWidget(self._make_row(key))

        layout.addWidget(self._make_divider())

        # Room scheduling toggle lives below the K-constraints.
        # It has no spinbox because enabling it is a binary choice - the
        # actual scheduling mode is selected by SchedulingModeFactory, not here.
        layout.addWidget(self._make_room_scheduling_row())

        # Push all rows to the top; leave empty space below.
        layout.addStretch(1)

    def _make_row(self, key: str) -> QWidget:
        """Build one checkbox + label + spinbox row for a single constraint."""
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 8, 0, 8)
        row.setSpacing(16)

        check = QCheckBox()
        check.setChecked(False)
        check.setStyleSheet(_CHECKBOX_STYLE)
        self._checks[key] = check

        text_vbox = QVBoxLayout()
        text_vbox.setSpacing(4)

        label = QLabel(_CONSTRAINT_LABELS[key])
        label.setStyleSheet(_ROW_LABEL_STYLE)

        desc = QLabel(_CONSTRAINT_DESCRIPTIONS[key])
        desc.setStyleSheet(_ROW_DESC_STYLE)
        desc.setWordWrap(True)
        
        text_vbox.addWidget(label)
        text_vbox.addWidget(desc)

        spin = QSpinBox()
        spin.setMinimum(_MIN_K[key])
        spin.setMaximum(_MAX_K[key])
        spin.setValue(_DEFAULT_K[key])
        spin.setFixedWidth(72)
        spin.setMinimumHeight(36)
        spin.setEnabled(False)  # disabled until the checkbox is checked
        spin.setStyleSheet("""
            QSpinBox {
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 16px;
                color: #0F172A;
                background: white;
            }
            QSpinBox:disabled { 
                color: #94A3B8; 
                background: #F1F5F9; 
                border: 1px solid #E2E8F0;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 24px;
            }
        """)
        self._spins[key] = spin

        # Link checkbox state → spinbox enabled state.
        check.toggled.connect(spin.setEnabled)

        row.addWidget(check)
        row.addLayout(text_vbox, stretch=1)
        row.addWidget(spin)

        return container

    def _make_room_scheduling_row(self) -> QWidget:
        """Build the boolean-only checkbox row for room scheduling.

        Unlike the K-constraint rows this row has no spinbox.  Checking it sets
        ConstraintSettings.room_scheduling_enabled=True, which causes
        SchedulingModeFactory to wire RoomAllocator and the room-based domain /
        placement components instead of the date-only defaults.

        A rooms file must be loaded via FileLoaderWidget before generating
        when this toggle is checked; AppService._prepare_engine() will raise a
        clear ValueError if the setting is on but no rooms are stored.
        """
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 8, 0, 8)
        row.setSpacing(16)

        check = QCheckBox()
        check.setChecked(False)
        check.setStyleSheet(_CHECKBOX_STYLE)
        self._room_scheduling_check = check

        text_vbox = QVBoxLayout()
        text_vbox.setSpacing(4)

        label = QLabel("Enable Room Scheduling")
        label.setStyleSheet(_ROW_LABEL_STYLE)

        desc = QLabel(
            "Assign each exam a time slot and rooms based on student count. "
            "Requires a rooms file to be loaded."
        )
        desc.setStyleSheet(_ROW_DESC_STYLE)
        desc.setWordWrap(True)

        text_vbox.addWidget(label)
        text_vbox.addWidget(desc)

        row.addWidget(check)
        row.addLayout(text_vbox, stretch=1)

        return container

    @staticmethod
    def _make_divider() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #E2E8F0;")
        return line

    # ------------------------------------------------------------------
    # Public API — used by EP-110 (validation) and EP-113 (save workflow)
    # ------------------------------------------------------------------

    def get_values(self) -> dict:
        """Return the current UI state as a flat dict matching ConstraintSettings fields.

        Example output:
            {
                "mandatory_gap_enabled": True,
                "mandatory_gap_k": 3,
                "all_gap_enabled": False,
                "all_gap_k": 3,
                ...
                "room_scheduling_enabled": False,
            }

        The room_scheduling_enabled key is always present so callers can pass
        this dict directly to ConstraintSettings.from_dict() without extra handling.
        """
        result = {}
        for key in _CONSTRAINT_LABELS:
            result[f"{key}_enabled"] = self._checks[key].isChecked()
            result[f"{key}_k"] = self._spins[key].value()
        # Boolean-only room scheduling toggle (no K parameter).
        result["room_scheduling_enabled"] = self._room_scheduling_check.isChecked()
        return result

    def set_values(self, values: dict) -> None:
        """Populate the form from a dict with the same shape as get_values() output."""
        for key in _CONSTRAINT_LABELS:
            enabled = values.get(f"{key}_enabled", False)
            k_val   = values.get(f"{key}_k", _DEFAULT_K[key])
            self._checks[key].setChecked(enabled)
            self._spins[key].setValue(k_val)
        # Restore room scheduling toggle; defaults to off if key is absent
        # (e.g. loading settings saved before this feature was added).
        if self._room_scheduling_check is not None:
            self._room_scheduling_check.setChecked(
                values.get("room_scheduling_enabled", False)
            )


    def get_settings(self) -> ConstraintSettings:
        """Build a typed ConstraintSettings object from the current UI state."""
        return ConstraintSettings.from_dict(self.get_values())

    def set_settings(self, settings: ConstraintSettings) -> None:
        """Populate the UI controls from a typed ConstraintSettings object."""
        self.set_values(settings.to_dict())
    