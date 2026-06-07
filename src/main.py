import multiprocessing
import sys

from PyQt5.QtWidgets import QApplication

from src.main_window import MainWindow


def main():
    """
    Main entry point for the PyQt5 desktop application.

    Starts two processes:
      UI Process     — this process; runs PyQt5 and AppService (reader-only).
      Engine Process — spawned by EngineProcess(); runs solve_to_disk() with
                       its own GIL so the UI is never blocked by computation.
    """
    # Required on Windows: prevents recursive subprocess spawning when the
    # executable is frozen (PyInstaller / cx_Freeze). Safe no-op on macOS/Linux.
    multiprocessing.freeze_support()

    # ── Start the Engine Process before the UI ────────────────────────────
    from src.presenter.app_service import AppService
    from src.presenter.engine_process import EngineProcess

    service = AppService.getInstance()
    service._engine_process = EngineProcess()   # spawns the Engine Process now

    # ── Start the UI Process (this process) ──────────────────────────────
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()