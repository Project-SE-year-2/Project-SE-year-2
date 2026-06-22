"""Tests for ConstraintConfigWidget (EP-109)."""

import sys
import unittest
from PyQt5.QtWidgets import QApplication, QCheckBox, QSpinBox

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from src.views.settings_screen.constraint_config_widget import ConstraintConfigWidget

KEYS = ["mandatory_gap", "all_gap", "elective_conflicts", "spread", "daily_cap"]


class TestConstraintConfigWidgetStructure(unittest.TestCase):

    def setUp(self):
        self.widget = ConstraintConfigWidget()

    # ------------------------------------------------------------------
    # Internal dictionaries
    # ------------------------------------------------------------------

    def test_checks_dict_has_all_five_keys(self):
        """_checks must contain one QCheckBox per constraint."""
        self.assertEqual(set(self.widget._checks.keys()), set(KEYS))

    def test_spins_dict_has_all_five_keys(self):
        """_spins must contain one QSpinBox per constraint."""
        self.assertEqual(set(self.widget._spins.keys()), set(KEYS))

    def test_checks_values_are_checkboxes(self):
        for key in KEYS:
            self.assertIsInstance(self.widget._checks[key], QCheckBox)

    def test_spins_values_are_spinboxes(self):
        for key in KEYS:
            self.assertIsInstance(self.widget._spins[key], QSpinBox)

    # ------------------------------------------------------------------
    # Initial state
    # ------------------------------------------------------------------

    def test_all_checkboxes_unchecked_by_default(self):
        """No constraint must be enabled when the widget first loads."""
        for key in KEYS:
            self.assertFalse(self.widget._checks[key].isChecked(), msg=key)

    def test_all_spinboxes_disabled_by_default(self):
        """All spinboxes must be disabled until their checkbox is checked."""
        for key in KEYS:
            self.assertFalse(self.widget._spins[key].isEnabled(), msg=key)


class TestConstraintConfigWidgetLinking(unittest.TestCase):
    """Checkbox ↔ spinbox enabled-state link (acceptance criterion)."""

    def setUp(self):
        self.widget = ConstraintConfigWidget()

    def test_checking_enables_spinbox(self):
        """Checking a constraint checkbox must enable its paired spinbox."""
        for key in KEYS:
            self.widget._checks[key].setChecked(True)
            self.assertTrue(self.widget._spins[key].isEnabled(), msg=key)

    def test_unchecking_disables_spinbox(self):
        """Unchecking a constraint checkbox must disable its paired spinbox."""
        for key in KEYS:
            self.widget._checks[key].setChecked(True)
            self.widget._checks[key].setChecked(False)
            self.assertFalse(self.widget._spins[key].isEnabled(), msg=key)

    def test_each_checkbox_only_affects_its_own_spinbox(self):
        """Checking one constraint must not enable any other spinbox."""
        self.widget._checks["all_gap"].setChecked(True)
        for key in KEYS:
            if key != "all_gap":
                self.assertFalse(self.widget._spins[key].isEnabled(), msg=key)

    def test_toggle_sequence(self):
        """Repeated check/uncheck cycles must leave the spinbox in the correct state."""
        check = self.widget._checks["spread"]
        spin = self.widget._spins["spread"]
        for _ in range(3):
            check.setChecked(True)
            self.assertTrue(spin.isEnabled())
            check.setChecked(False)
            self.assertFalse(spin.isEnabled())


class TestConstraintConfigWidgetAPI(unittest.TestCase):
    """get_values() and set_values() public API."""

    def setUp(self):
        self.widget = ConstraintConfigWidget()

    def test_get_values_returns_all_keys(self):
        """get_values() must include enabled and k keys for every constraint."""
        values = self.widget.get_values()
        for key in KEYS:
            self.assertIn(f"{key}_enabled", values)
            self.assertIn(f"{key}_k", values)

    def test_get_values_reflects_checkbox_state(self):
        self.widget._checks["daily_cap"].setChecked(True)
        self.assertTrue(self.widget.get_values()["daily_cap_enabled"])

    def test_get_values_reflects_spinbox_value(self):
        self.widget._checks["spread"].setChecked(True)
        self.widget._spins["spread"].setValue(14)
        self.assertEqual(self.widget.get_values()["spread_k"], 14)

    def test_set_values_enables_checkbox(self):
        self.widget.set_values({"all_gap_enabled": True, "all_gap_k": 5})
        self.assertTrue(self.widget._checks["all_gap"].isChecked())

    def test_set_values_sets_spinbox_value(self):
        self.widget.set_values({"mandatory_gap_enabled": True, "mandatory_gap_k": 7})
        self.assertEqual(self.widget._spins["mandatory_gap"].value(), 7)

    def test_set_values_then_get_values_roundtrip(self):
        """set_values followed by get_values must return the same data."""
        original = {
            "mandatory_gap_enabled": True,  "mandatory_gap_k": 4,
            "all_gap_enabled": False,        "all_gap_k": 3,
            "elective_conflicts_enabled": True, "elective_conflicts_k": 2,
            "spread_enabled": True,          "spread_k": 10,
            "daily_cap_enabled": False,      "daily_cap_k": 3,
        }
        self.widget.set_values(original)
        result = self.widget.get_values()
        self.assertEqual(result, original)

    def test_set_values_partial_dict_leaves_others_unchanged(self):
        """Passing a partial dict must not crash and must leave other fields at defaults."""
        self.widget.set_values({"daily_cap_enabled": True, "daily_cap_k": 2})
        # Other checkboxes must still be unchecked
        self.assertFalse(self.widget._checks["all_gap"].isChecked())


if __name__ == "__main__":
    unittest.main()
