"""
SaveEditWorker — background QThread for persisting exam edits.

Runs save_exam_edit() off the UI thread so disk I/O and score
recalculation don't freeze the calendar while the user waits.

Signals:
    finished()        — emitted on success; caller exits edit mode.
    error(str)        — emitted on failure; caller shows the message inline.
"""

from __future__ import annotations

from datetime import date
from PyQt5.QtCore import QThread, pyqtSignal


class SaveEditWorker(QThread):
    finished = pyqtSignal()
    error    = pyqtSignal(str)

    def __init__(
        self,
        service,
        period_id: str,
        index: int,
        course_number: str,
        new_date: date,
        new_time_slot: str | None,
        new_room_keys: list[str],
        parent=None,
    ):
        super().__init__(parent)
        self._service       = service
        self._period_id     = period_id
        self._index         = index
        self._course_number = course_number
        self._new_date      = new_date
        self._new_time_slot = new_time_slot
        self._new_room_keys = new_room_keys

    def run(self) -> None:
        try:
            self._service.save_exam_edit(
                period_id     = self._period_id,
                index         = self._index,
                course_number = self._course_number,
                new_date      = self._new_date,
                new_time_slot = self._new_time_slot,
                new_room_keys = self._new_room_keys,
            )
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))
