from PyQt5.QtWidgets import QCalendarWidget, QAbstractItemView
from datetime import date

from PyQt5.QtCore import Qt, QDate, QRect, QRectF, QEvent, pyqtSignal, QLocale
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QBrush, QTextCharFormat

class ScheduleCalendarWidget(QCalendarWidget):
    exam_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        """Initialize the calendar widget with custom styles, disable unwanted features,
            and set up the color palette for exam badges."""
        super().__init__(parent)

        self.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setNavigationBarVisible(False)
        self.setSelectionMode(QCalendarWidget.NoSelection)
        self.setFocusPolicy(Qt.NoFocus)

        self.exams_by_date = {}

        # NoSelection mode blocks the built-in clicked() signal, so we install
        # an event filter directly on the internal table-view's viewport instead.
        for view in self.findChildren(QAbstractItemView):
            view.viewport().installEventFilter(self)
            self._calendar_view = view   # keep a reference for hit-testing
            break

        header_format = QTextCharFormat()
        header_format.setForeground(QColor("#9CA3AF"))
        header_format.setFontWeight(QFont.Bold)
        # Apply the header format to the weekday headers (1=Monday, 7=Sunday)
        for day in range(1, 8):
            self.setWeekdayTextFormat(day, header_format)

        from src.styles.calendar_style import CALENDAR_STYLE
        self.setStyleSheet(CALENDAR_STYLE)

        self.color_palette = [
            (QColor("#1E1B4B"), QColor("#6366F1"), QColor("#E0E7FF")), # Purple
            (QColor("#082F49"), QColor("#0EA5E9"), QColor("#E0F2FE")), # Blue
            (QColor("#422006"), QColor("#F59E0B"), QColor("#FEF3C7")), # Orange
            (QColor("#064E3B"), QColor("#10B981"), QColor("#D1FAE5")), # Green
        ]

    def update_schedule(self, schedule_data: list):
        """Update the calendar with new schedule data, organizing exams by date and refreshing the display."""
        self.exams_by_date.clear()
        # Convert incoming schedule data into a mapping of QDate to exam lists
        for exam in schedule_data:
            qdate = self._to_qdate(exam.get("exam_date"))
            if qdate.isValid():
                self.exams_by_date.setdefault(qdate, []).append(exam)
        # After updating the exams_by_date mapping, refresh the calendar display
        if self.exams_by_date:
            first_date = min(self.exams_by_date.keys())
            self.setCurrentPage(first_date.year(), first_date.month())
            
        self.updateCells()

    def _to_qdate(self, value):
        """Helper method to convert various date formats (QDate, datetime.date, string) into a QDate object."""
        if isinstance(value, QDate):
            return value
        if isinstance(value, date):
            return QDate(value.year, value.month, value.day)
        if isinstance(value, str):
            return QDate.fromString(value, "yyyy-MM-dd")
        return QDate()

    def paintCell(self, painter: QPainter, rect: QRect, date: QDate):
        """Override the default cell painting to include custom rendering for exam badges on their
             respective dates."""
        painter.save()
        
        painter.fillRect(rect, QColor("#0B1121"))
            
        if date.month() != self.monthShown():
            painter.setPen(QColor("#374151")) 
        else:
            painter.setPen(QColor("#F9FAFB")) 
            
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.drawText(rect.adjusted(10, 10, 0, 0), Qt.AlignTop | Qt.AlignLeft, str(date.day()))
        
       # Draw Exam Badges
        if date in self.exams_by_date:
            exams = self.exams_by_date[date]
            y_offset = rect.top() + 35
            # Limit to 2 badges per cell to prevent overflow, with a visual indication if more exams exist
            for i, exam in enumerate(exams):
                if i > 0 and y_offset + 55 > rect.bottom():
                    break 
                    
                course_name = exam.get("course_name", "Exam")
                
                color_index = hash(course_name) % len(self.color_palette)
                bg_color, border_color, text_color = self.color_palette[color_index]
                
                badge_rect = QRectF(rect.left() + 8, y_offset, rect.width() - 16, 55)
                
                pen = QPen(border_color)
                pen.setWidth(1)
                painter.setPen(pen)
                painter.setBrush(QBrush(bg_color))
                painter.drawRoundedRect(badge_rect, 6.0, 6.0) 
                
                painter.setPen(text_color)
                
                font = QFont("Segoe UI", 10, QFont.Bold)
                painter.setFont(font)
                text_rect = badge_rect.adjusted(10, 8, -10, 0)
                painter.drawText(text_rect, Qt.AlignTop | Qt.AlignLeft, f"📄 {course_name}")
                
                
                y_offset += 60
                
        painter.restore()

    # ------------------------------------------------------------------
    # Click detection via event filter (works even with NoSelection mode)
    # ------------------------------------------------------------------

    def eventFilter(self, source, event):
        """Intercept mouse-press events on the calendar viewport to detect
        which date was clicked and emit exam_clicked when an exam exists."""
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            index = self._calendar_view.indexAt(event.pos())
            if index.isValid():
                clicked_date = self.dateForIndex(index)
                if clicked_date.isValid() and clicked_date in self.exams_by_date:
                    self.exam_clicked.emit(self.exams_by_date[clicked_date][0])
        return super().eventFilter(source, event)

    def dateForIndex(self, index):
        """Convert a QModelIndex from the internal table view into a QDate."""
        # QCalendarWidget's model stores the date as Qt.DisplayRole text
        # but we can reconstruct the date from year/month + cell position.
        # Row 0 is the header (day names), rows 1-6 are weeks; col 0-6 are days.
        row = index.row()       # 1–6 (row 0 = day-name header)
        col = index.column()    # 0=Sun … 6=Sat  (depends on firstDayOfWeek)

        if row < 1:             # clicked on the day-name header row
            return QDate()

        # Walk from the first cell of the shown month-page
        first_day_of_month = QDate(self.yearShown(), self.monthShown(), 1)
        # The calendar grid starts on the column matching the first day's weekday
        first_col = (first_day_of_month.dayOfWeek() % 7)   # Sun=0 … Sat=6
        cell_index = (row - 1) * 7 + col
        day_offset  = cell_index - first_col
        return first_day_of_month.addDays(day_offset)
