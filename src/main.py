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

    Room scheduling architecture (EP-129 / EP-130 / EP-132–EP-134):
      ConstraintSettings.room_scheduling_enabled is the single mode switch.

      Solver layer — SchedulingModeFactory wires mode-specific components:
        - DateOnlyDomainProvider          → candidates are date objects (default)
        - RoomSchedulingDomainProvider    → candidates are ExamBlock(date, slot)
        - RoomPlacementFactory            → converts ExamBlock → ExamPlacement with rooms
        - RoomSchedulingFeasibilityChecker → validates student count and total capacity
      BacktrackingSolver is mode-agnostic; it never reads room_scheduling_enabled.

      Constraint layer — ConstraintChecker adds RoomAndSlotConstraint when enabled:
        - Room exclusivity: one room per (date, slot) across all exams
        - Room capacity:    total capacity >= num_students per exam
        - Bypasses automatically when all placements are date-only (no rooms)
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