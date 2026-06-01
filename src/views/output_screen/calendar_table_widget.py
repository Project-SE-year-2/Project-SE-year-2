from PyQt5.QtWidgets import QCalendarWidget
from PyQt5.QtCore import Qt, QDate, QRect, QRectF, pyqtSignal, QLocale
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QBrush, QTextCharFormat

class ScheduleCalendarWidget(QCalendarWidget):
    exam_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
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
        self.exams_by_date.clear()
        for exam in schedule_data:
            date_str = exam.get("exam_date", "")
            if date_str:
                qdate = QDate.fromString(date_str, "yyyy-MM-dd")
                if qdate not in self.exams_by_date:
                    self.exams_by_date[qdate] = []
                self.exams_by_date[qdate].append(exam)
        
        if self.exams_by_date:
            first_date = min(self.exams_by_date.keys())
            self.setCurrentPage(first_date.year(), first_date.month())
            
        self.updateCells()

    def paintCell(self, painter: QPainter, rect: QRect, date: QDate):
        painter.save()
        
        painter.fillRect(rect, QColor("#0B1121"))
            
        if date.month() != self.monthShown():
            painter.setPen(QColor("#374151")) 
        else:
            painter.setPen(QColor("#F9FAFB")) 
            
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.drawText(rect.adjusted(10, 10, 0, 0), Qt.AlignTop | Qt.AlignLeft, str(date.day()))
        
       # Draw Exam Badges
        # Draw Exam Badges
        if date in self.exams_by_date:
            exams = self.exams_by_date[date]
            y_offset = rect.top() + 35 # מתחילים קצת יותר גבוה
            
            for i, exam in enumerate(exams):
                # אנחנו בודקים אם יש מקום רק מהמבחן השני והלאה!
                # המבחן הראשון (i == 0) יצויר תמיד, בכל מצב.
                if i > 0 and y_offset + 55 > rect.bottom():
                    break 
                    
                course_name = exam.get("course_name", "Exam")
                
                color_index = hash(course_name) % len(self.color_palette)
                bg_color, border_color, text_color = self.color_palette[color_index]
                
                # גודל התגית הותאם למסכי High-DPI
                badge_rect = QRectF(rect.left() + 8, y_offset, rect.width() - 16, 55)
                
                pen = QPen(border_color)
                pen.setWidth(1)
                painter.setPen(pen)
                painter.setBrush(QBrush(bg_color))
                painter.drawRoundedRect(badge_rect, 6.0, 6.0) 
                
                painter.setPen(text_color)
                
                # פונט לקורס
                font = QFont("Segoe UI", 10, QFont.Bold)
                painter.setFont(font)
                text_rect = badge_rect.adjusted(10, 8, -10, 0)
                painter.drawText(text_rect, Qt.AlignTop | Qt.AlignLeft, f"📄 {course_name}")
                
                # # פונט לשעה
                # font = QFont("Segoe UI", 8)
                # painter.setFont(font)
                # time_rect = badge_rect.adjusted(28, 28, -10, 0)
                # painter.drawText(time_rect, Qt.AlignTop | Qt.AlignLeft, "09:00 - 12:00")
                
                y_offset += 60
                
        painter.restore()

    def _on_date_clicked(self, date: QDate):
        # חשוב: כאן אנחנו בודקים אם יש מבחן ומשדרים אותו החוצה
        if date in self.exams_by_date:
            # אנחנו לוקחים את המבחן הראשון שיש באותו יום
            exam_data = self.exams_by_date[date][0]
            print(f"DEBUG: Emitting exam_clicked for {exam_data}") # תראי אם זה מודפס בטרמינל
            self.exam_clicked.emit(exam_data)


# from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
# from PyQt5.QtCore import pyqtSignal, Qt
# from PyQt5.QtGui import QColor

# class CalendarTableWidget(QTableWidget):
#     """
#     A shared calendar widget utilized by both the Input and Output screens.
#     Operates in two distinct modes: 'period' (availability selection) and 'schedule' (final output).
#     """
    
#     # Emits a dictionary containing the date and, if applicable, the course data
#     day_clicked = pyqtSignal(dict)

#     def __init__(self, mode="period", parent=None):
#         """
#         Initializes the calendar grid.
#         Mode must be either 'period' or 'schedule'.
#         """
#         # Initialize with 6 rows (max weeks in a month span) and 7 columns (days)
#         super().__init__(6, 7, parent)
#         self.mode = mode
#         self._setup_ui()
        
#         # Connect the built-in cell click event to our custom handler
#         self.cellClicked.connect(self._handle_cell_click)

#     def _setup_ui(self):
#         """
#         Configures the grid structure, headers, and applies the dark mode styling.
#         """
#         self.setHorizontalHeaderLabels(['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'])
#         self.verticalHeader().setVisible(False)
        
#         # Expand cells dynamically so the full schedule fits on one screen
#         self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
#         self.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
#         # Disable manual text editing by the user
#         self.setEditTriggers(QTableWidget.NoEditTriggers)
#         self.setFocusPolicy(Qt.NoFocus)

#         self.setStyleSheet("""
#             QTableWidget {
#                 background-color: #1e1e1e;
#                 color: #ffffff;
#                 gridline-color: #444444;
#                 border: 1px solid #333333;
#                 font-size: 13px;
#             }
#             QHeaderView::section {
#                 background-color: #2d2d30;
#                 color: #ffffff;
#                 padding: 5px;
#                 border: 1px solid #444444;
#                 font-weight: bold;
#             }
#             QTableWidget::item {
#                 padding: 5px;
#             }
#         """)

#     def render_period_mode(self, days_data):
#         """
#         Renders the calendar for the Input screen.
#         Expected input: list of dicts [{'date': '2026-06-01', 'status': 'allowed'|'forbidden'|'outside'}]
#         Colors: Green (allowed), Red (forbidden), Grey (outside).
#         """
#         if self.mode != "period":
#             return

#         self.clearContents()
        
#         row, col = 0, 0
#         for day in days_data:
#             item = QTableWidgetItem(day.get('date', ''))
#             item.setTextAlignment(Qt.AlignTop | Qt.AlignLeft)
            
#             # Apply specific color coding based on the ticket constraints
#             status = day.get('status')
#             if status == 'allowed':
#                 item.setBackground(QColor("#2e7d32"))  # Dark Green
#             elif status == 'forbidden':
#                 item.setBackground(QColor("#c62828"))  # Dark Red
#             else:
#                 item.setBackground(QColor("#424242"))  # Grey for outside range
            
#             # Store the underlying data package inside the item for retrieval on click
#             item.setData(Qt.UserRole, day)
#             self.setItem(row, col, item)
            
#             # Advance grid coordinates
#             col += 1
#             if col > 6:
#                 col = 0
#                 row += 1

#     def render_schedule_mode(self, schedule_data):
#         """
#         Renders the final schedule for the Output screen.
#         Expected input: list of dicts [{'date': '2026-06-01', 'course_name': 'Data Structures', 'full_data': {...}}]
#         """
#         if self.mode != "schedule":
#             return

#         self.clearContents()
        
#         row, col = 0, 0
#         for day in schedule_data:
#             date_str = day.get('date', '')
#             course_name = day.get('course_name', '')
            
#             # Shorten course names where needed so they fit the cell without breaking the layout
#             display_name = course_name
#             if len(display_name) > 15:
#                 display_name = display_name[:12] + "..."
                
#             cell_text = f"{date_str}\n\n{display_name}" if display_name else date_str
            
#             item = QTableWidgetItem(cell_text)
#             item.setTextAlignment(Qt.AlignCenter)
#             item.setBackground(QColor("#2d2d30"))
            
#             # Store the full course data package inside the item
#             item.setData(Qt.UserRole, day)
#             self.setItem(row, col, item)
            
#             # Advance grid coordinates
#             col += 1
#             if col > 6:
#                 col = 0
#                 row += 1

#     def _handle_cell_click(self, row, col):
#         """
#         Internal handler for cell clicks. Extracts the stored data and emits the custom signal.
#         """
#         item = self.item(row, col)
#         if item is not None:
#             # Retrieve the dictionary stored via Qt.UserRole
#             day_data = item.data(Qt.UserRole)
#             if day_data:
#                 self.day_clicked.emit(day_data)