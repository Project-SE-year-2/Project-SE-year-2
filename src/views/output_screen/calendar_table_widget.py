from PyQt5.QtWidgets import QCalendarWidget
from datetime import date

from PyQt5.QtCore import Qt, QDate, QRect, QRectF, pyqtSignal, QLocale
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
        self.clicked.connect(self._on_date_clicked)

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

    def _on_date_clicked(self, date: QDate):
        """Handle clicks on calendar cells by checking if the clicked date has associated exams and 
            emitting the exam data if present."""
        if date in self.exams_by_date:
            exam_data = self.exams_by_date[date][0]
            self.exam_clicked.emit(exam_data)
