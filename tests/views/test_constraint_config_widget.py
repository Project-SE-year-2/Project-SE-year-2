"""Tests for ConstraintConfigWidget (EP-109 + EP-110 validation rules)."""

import sys
import unittest
from PyQt5.QtWidgets import QApplication, QCheckBox, QSpinBox

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from src.views.settings_screen.constraint_config_widget import ConstraintConfigWidget
from src.models.constraint_settings import ConstraintSettings

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


class TestConstraintConfigWidgetValidation(unittest.TestCase):
    """EP-110 — spinbox minimum boundaries block out-of-bounds entries."""

    def setUp(self):
        self.widget = ConstraintConfigWidget()

    # elective_conflicts allows 0 (zero conflicts is valid)
    def test_elective_conflicts_min_is_zero(self):
        self.assertEqual(self.widget._spins["elective_conflicts"].minimum(), 0)

    # all gap / calendar constraints must start at 0
    def test_mandatory_gap_min_is_zero(self):
        self.assertEqual(self.widget._spins["mandatory_gap"].minimum(), 0)

    def test_all_gap_min_is_zero(self):
        self.assertEqual(self.widget._spins["all_gap"].minimum(), 0)

    def test_spread_min_is_zero(self):
        self.assertEqual(self.widget._spins["spread"].minimum(), 0)

    def test_daily_cap_min_is_zero(self):
        self.assertEqual(self.widget._spins["daily_cap"].minimum(), 0)

    def test_spinbox_clamps_below_minimum_for_gap_constraints(self):
        """Gap spinboxes must accept 0 so disabled settings can round-trip without clamping."""
        spin = self.widget._spins["all_gap"]
        spin.setValue(0)
        self.assertEqual(spin.value(), 0)

    def test_spinbox_accepts_zero_for_elective_conflicts(self):
        """elective_conflicts spinbox must accept 0 as a valid value."""
        spin = self.widget._spins["elective_conflicts"]
        spin.setValue(0)
        self.assertEqual(spin.value(), 0)

    def test_all_spinboxes_respect_max_boundary(self):
        """No spinbox must accept a value above its defined maximum."""
        maxes = {
            "mandatory_gap": 30, "all_gap": 30,
            "elective_conflicts": 10, "spread": 60, "daily_cap": 10,
        }
        for key, max_val in maxes.items():
            spin = self.widget._spins[key]
            spin.setValue(max_val + 999)
            self.assertEqual(spin.value(), max_val, msg=key)


if __name__ == "__main__":
    unittest.main()


class TestConstraintConfigWidgetSettingsAPI(unittest.TestCase):
    """Typed ConstraintSettings API tests for ConstraintConfigWidget."""

    def setUp(self):
        """Create a fresh widget before each settings API test."""
        self.widget = ConstraintConfigWidget()

    def test_get_settings_returns_constraint_settings_object(self):
        """Verify that get_settings returns a typed ConstraintSettings object."""
        settings = self.widget.get_settings()

        self.assertIsInstance(settings, ConstraintSettings)

    def test_get_settings_preserves_enabled_flags_and_k_values(self):
        """Verify that UI checkbox and spinbox values are copied into ConstraintSettings."""
        self.widget._checks["daily_cap"].setChecked(True)
        self.widget._spins["daily_cap"].setValue(4)

        settings = self.widget.get_settings()

        self.assertTrue(settings.daily_cap_enabled)
        self.assertEqual(settings.daily_cap_k, 4)

    def test_set_settings_populates_ui_from_constraint_settings(self):
        """Verify that set_settings loads ConstraintSettings values into the UI controls."""
        settings = ConstraintSettings(
            all_gap_enabled=True,
            all_gap_k=6,
            daily_cap_enabled=True,
            daily_cap_k=2,
        )

        self.widget.set_settings(settings)

        self.assertTrue(self.widget._checks["all_gap"].isChecked())
        self.assertEqual(self.widget._spins["all_gap"].value(), 6)
        self.assertTrue(self.widget._checks["daily_cap"].isChecked())
        self.assertEqual(self.widget._spins["daily_cap"].value(), 2)

    def test_set_settings_then_get_settings_roundtrip(self):
        """Verify that ConstraintSettings can round-trip through the widget without data loss."""
        original = ConstraintSettings(
            mandatory_gap_enabled=True,
            mandatory_gap_k=3,
            all_gap_enabled=True,
            all_gap_k=5,
            elective_conflicts_enabled=True,
            elective_conflicts_k=1,
            spread_enabled=True,
            spread_k=12,
            daily_cap_enabled=True,
            daily_cap_k=2,
        )

        self.widget.set_settings(original)
        result = self.widget.get_settings()

        self.assertEqual(result, original)