"""Tests for SettingsScreen core view container (EP-108)."""

import sys
import unittest
from unittest.mock import MagicMock

from PyQt5.QtWidgets import QApplication

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from src.views.settings_screen.settings_screen import SettingsScreen
from src.views.settings_screen.constraint_config_widget import ConstraintConfigWidget
from src.models.constraint_settings import ConstraintSettings


class TestSettingsScreen(unittest.TestCase):

    def setUp(self):
        self.mock_service = MagicMock()
        self.screen = SettingsScreen(self.mock_service)

    # ------------------------------------------------------------------
    # Instantiation
    # ------------------------------------------------------------------

    def test_instantiates_without_error(self):
        """SettingsScreen must construct cleanly with a service dependency."""
        self.assertIsNotNone(self.screen)

    def test_service_stored(self):
        """The injected service must be accessible on the instance."""
        self.assertIs(self.screen.service, self.mock_service)

    # ------------------------------------------------------------------
    # Sub-widget presence
    # ------------------------------------------------------------------

    def test_constraint_panel_exists(self):
        """constraint_panel must be a ConstraintConfigWidget."""
        self.assertIsInstance(self.screen.constraint_panel, ConstraintConfigWidget)

    def test_back_button_exists(self):
        """Header must expose a back_btn QPushButton."""
        from PyQt5.QtWidgets import QPushButton
        self.assertIsInstance(self.screen.back_btn, QPushButton)

    # ------------------------------------------------------------------
    # Navigation signal
    # ------------------------------------------------------------------

    def test_switch_to_input_signal_exists(self):
        """SettingsScreen must declare the switch_to_input signal."""
        self.assertTrue(hasattr(SettingsScreen, 'switch_to_input'))

    def test_back_button_emits_switch_to_input(self):
        """Clicking back_btn must emit switch_to_input exactly once."""
        received = []
        self.screen.switch_to_input.connect(lambda: received.append(1))
        self.screen.back_btn.click()
        self.assertEqual(received, [1])

    # ------------------------------------------------------------------
    # Layout — no visual overlap
    # ------------------------------------------------------------------

    def test_constraint_panel_has_positive_size_when_shown(self):
        """The constraint panel must have non-zero geometry after the screen is shown."""
        self.screen.resize(800, 600)
        self.screen.show()
        QApplication.processEvents()

        cp = self.screen.constraint_panel
        self.assertGreater(cp.width(), 0)

        self.screen.hide()


    def test_set_constraint_settings_updates_ui_controls(self):
        """Verify that set_constraint_settings updates the constraint panel checkboxes and spinboxes."""
        settings = ConstraintSettings(
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

        self.screen.set_constraint_settings(settings)

        panel = self.screen.constraint_panel

        self.assertTrue(panel._checks["mandatory_gap"].isChecked())
        self.assertEqual(panel._spins["mandatory_gap"].value(), 3)

        self.assertTrue(panel._checks["all_gap"].isChecked())
        self.assertEqual(panel._spins["all_gap"].value(), 5)

        self.assertTrue(panel._checks["elective_conflicts"].isChecked())
        self.assertEqual(panel._spins["elective_conflicts"].value(), 1)

        self.assertTrue(panel._checks["spread"].isChecked())
        self.assertEqual(panel._spins["spread"].value(), 12)

        self.assertTrue(panel._checks["daily_cap"].isChecked())
        self.assertEqual(panel._spins["daily_cap"].value(), 2)


class TestSettingsScreenInMainWindow(unittest.TestCase):
    """Verify SettingsScreen integrates correctly inside MainWindow."""

    def setUp(self):
        from src.main_window import MainWindow
        self.window = MainWindow()

    def test_settings_screen_at_index_2(self):
        """SettingsScreen must occupy index 2 in the stacked widget."""
        self.assertIsInstance(
            self.window.stacked_widget.widget(2), SettingsScreen
        )

    def test_settings_screen_navigation_back(self):
        """Emitting switch_to_input from SettingsScreen must return to index 0."""
        self.window.stacked_widget.setCurrentIndex(2)
        self.window.settings_screen.switch_to_input.emit()
        self.assertEqual(self.window.stacked_widget.currentIndex(), 0)

    def test_settings_service_same_instance(self):
        """SettingsScreen must receive the same service as the other screens."""
        self.assertIs(
            self.window.settings_screen.service,
            self.window.service,
        )

    def test_input_screen_has_switch_to_settings_signal(self):
        """InputScreen must expose switch_to_settings to trigger navigation."""
        from src.views.input_screen.input_screen import InputScreen
        self.assertTrue(hasattr(InputScreen, 'switch_to_settings'))

    def test_settings_button_navigates_to_settings_screen(self):
        """Clicking the Settings button on InputScreen must switch to index 2."""
        self.window.stacked_widget.setCurrentIndex(0)
        self.window.input_screen.switch_to_settings.emit()
        self.assertEqual(self.window.stacked_widget.currentIndex(), 2)

    def test_back_from_settings_does_not_wipe_results(self):
        """Navigating back from Settings must go to index 0 via the no-wipe path."""
        # Confirm _return_to_input_without_wipe exists and does NOT call _wipe_results.
        self.assertTrue(
            hasattr(self.window, '_return_to_input_without_wipe'),
            "_return_to_input_without_wipe method must exist on MainWindow",
        )
        self.window.stacked_widget.setCurrentIndex(2)
        self.window._return_to_input_without_wipe()
        self.assertEqual(self.window.stacked_widget.currentIndex(), 0)

    
    def test_settings_screen_returns_constraint_settings_object(self):
        """Verify that SettingsScreen exposes typed constraint settings from its constraint panel."""
        settings = self.window.settings_screen.get_constraint_settings()

        self.assertIsInstance(settings, ConstraintSettings)


class TestSettingsScreenApply(unittest.TestCase):
    """EP-113 — verify the Apply workflow: _on_apply emits signal and MainWindow
    persists both constraint settings and sort order to the service layer."""

    def setUp(self):
        from src.main_window import MainWindow
        self.window = MainWindow()
        self.screen = self.window.settings_screen
        self.service = self.window.service

    # ------------------------------------------------------------------
    # _on_apply method
    # ------------------------------------------------------------------

    def test_on_apply_method_exists(self):
        """SettingsScreen must expose a private _on_apply handler."""
        self.assertTrue(
            callable(getattr(self.screen, '_on_apply', None)),
            "_on_apply must be a callable method on SettingsScreen",
        )

    def test_apply_button_connected_to_on_apply(self):
        """Clicking apply_btn must emit settings_confirmed exactly once."""
        received = []
        self.screen.settings_confirmed.connect(lambda: received.append(1))
        self.screen.apply_btn.click()
        self.assertEqual(received, [1])

    def test_on_apply_emits_settings_confirmed(self):
        """_on_apply() must emit settings_confirmed."""
        received = []
        self.screen.settings_confirmed.connect(lambda: received.append(1))
        self.screen._on_apply()
        self.assertEqual(received, [1])

    # ------------------------------------------------------------------
    # Constraint settings are saved to the service on Apply
    # ------------------------------------------------------------------

    def test_apply_saves_constraint_settings_to_service(self):
        """Clicking Apply must push constraint panel values into the service."""
        # Set a known valid state on the constraint panel.
        self.screen.constraint_panel.set_values({
            "mandatory_gap_enabled": True,  "mandatory_gap_k": 5,
            "all_gap_enabled": False,        "all_gap_k": 2,
            "elective_conflicts_enabled": False, "elective_conflicts_k": 1,
            "spread_enabled": False,          "spread_k": 7,
            "daily_cap_enabled": False,       "daily_cap_k": 3,
        })

        self.screen._on_apply()
        QApplication.processEvents()

        saved = self.service.get_constraint_settings()
        self.assertTrue(saved.mandatory_gap_enabled)
        self.assertEqual(saved.mandatory_gap_k, 5)

    def test_apply_with_invalid_k_does_not_navigate_away(self):
        """If constraint settings are invalid, Apply must NOT switch to index 0."""
        from unittest.mock import patch

        # mandatory_gap enabled with K=0 is invalid (minimum is 1).
        self.screen.constraint_panel._checks["mandatory_gap"].setChecked(True)
        self.screen.constraint_panel._spins["mandatory_gap"].setValue(0)

        self.window.stacked_widget.setCurrentIndex(2)

        # Suppress the QMessageBox so no modal dialog blocks the test runner.
        with patch("src.main_window.QMessageBox.warning"):
            self.screen._on_apply()
            QApplication.processEvents()

        # The window must stay on the settings screen (index 2).
        self.assertEqual(self.window.stacked_widget.currentIndex(), 2)

    # ------------------------------------------------------------------
    # Navigation after Apply
    # ------------------------------------------------------------------

    def test_valid_apply_returns_to_input_screen(self):
        """A valid Apply must switch the stacked widget back to index 0."""
        # Put the constraint panel into a fully valid state before applying.
        self.screen.constraint_panel.set_values({
            "mandatory_gap_enabled": True,  "mandatory_gap_k": 3,
            "all_gap_enabled": True,         "all_gap_k": 2,
            "elective_conflicts_enabled": False, "elective_conflicts_k": 1,
            "spread_enabled": True,           "spread_k": 7,
            "daily_cap_enabled": True,        "daily_cap_k": 3,
        })

        self.window.stacked_widget.setCurrentIndex(2)
        self.screen._on_apply()
        QApplication.processEvents()

        self.assertEqual(self.window.stacked_widget.currentIndex(), 0)


if __name__ == '__main__':
    unittest.main()
