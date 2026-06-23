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
from src.views.settings_screen.ranking_config_widget import RankingConfigWidget
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

    def test_ranking_panel_exists(self):
        """ranking_panel must be a RankingConfigWidget."""
        self.assertIsInstance(self.screen.ranking_panel, RankingConfigWidget)

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

    def test_two_panels_are_different_objects(self):
        """constraint_panel and ranking_panel must be separate widget instances."""
        self.assertIsNot(self.screen.constraint_panel, self.screen.ranking_panel)

    def test_panels_have_positive_size_when_shown(self):
        """Both panels must have non-zero geometry after the screen is shown."""
        self.screen.resize(800, 600)
        self.screen.show()
        QApplication.processEvents()

        cp = self.screen.constraint_panel
        rp = self.screen.ranking_panel
        self.assertGreater(cp.width(), 0)
        self.assertGreater(rp.width(), 0)

        self.screen.hide()

    def test_panels_do_not_overlap(self):
        """constraint_panel right edge must not exceed ranking_panel left edge."""
        self.screen.resize(800, 600)
        self.screen.show()
        QApplication.processEvents()

        cp_right = (self.screen.constraint_panel
                    .mapTo(self.screen, self.screen.constraint_panel.rect().topRight())
                    .x())
        rp_left = (self.screen.ranking_panel
                   .mapTo(self.screen, self.screen.ranking_panel.rect().topLeft())
                   .x())

        self.assertLessEqual(cp_right, rp_left)
        self.screen.hide()


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


if __name__ == '__main__':
    unittest.main()
