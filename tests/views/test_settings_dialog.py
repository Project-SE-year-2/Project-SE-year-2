import pytest
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QMessageBox

from src.main_window import MainWindow
from src.views.settings_screen.settings_dialog import SettingsDialog
from src.models.constraint_settings import ConstraintSettings


def test_settings_dialog_accepts_valid_input(qtbot):
    """Test that a valid settings input correctly sets the settings and accepts the dialog."""
    main_window = MainWindow()
    qtbot.addWidget(main_window)
    
    dialog = SettingsDialog(main_window.service, main_window)
    qtbot.addWidget(dialog)

    # Mock dialog.get_constraint_settings to return valid settings
    valid_settings = ConstraintSettings(daily_cap_enabled=True, daily_cap_k=2)
    dialog.get_constraint_settings = MagicMock(return_value=valid_settings)
    
    with patch.object(main_window.service, 'set_constraint_settings') as mock_set:
        with patch.object(dialog, 'accept') as mock_accept:
            # Recreate the connection logic from main_window._show_settings_dialog
            def on_confirmed():
                try:
                    settings = dialog.get_constraint_settings()
                except ValueError as exc:
                    return
                main_window.service.set_constraint_settings(settings)
                dialog.accept()

            dialog.settings_confirmed.connect(on_confirmed)
            
            # Simulate apply click
            dialog._on_apply()
            
            mock_set.assert_called_once_with(valid_settings)
            mock_accept.assert_called_once()


def test_main_window_handles_invalid_settings(qtbot):
    """Test that invalid settings result in a warning and do NOT accept the dialog."""
    main_window = MainWindow()
    qtbot.addWidget(main_window)
    
    # Mock QMessageBox to prevent actual popup blocking test
    with patch("src.main_window.QMessageBox.warning") as mock_warning:
        # Patch SettingsDialog to simulate user behavior
        with patch("src.main_window.SettingsDialog") as MockDialog:
            mock_dialog_instance = MockDialog.return_value
            # Make get_constraint_settings raise a ValueError
            mock_dialog_instance.get_constraint_settings.side_effect = ValueError("Invalid settings")
            
            # Intercept the connection to simulate emit later
            callbacks = []
            mock_dialog_instance.settings_confirmed.connect.side_effect = lambda cb: callbacks.append(cb)
            
            # Open the dialog (this binds the callbacks)
            main_window._show_settings_dialog()
            
            # Simulate the user clicking apply which would emit settings_confirmed
            assert len(callbacks) == 1
            callbacks[0]()
            
            # Verify warning was shown
            mock_warning.assert_called_once()
            assert "Invalid Constraint Settings" == mock_warning.call_args[0][1]
            assert "Invalid settings" in mock_warning.call_args[0][2]
            
            # Verify the dialog was NOT accepted
            mock_dialog_instance.accept.assert_not_called()
