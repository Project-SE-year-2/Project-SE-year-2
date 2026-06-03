"""
Stylesheet for the ScheduleCalendarWidget.
Implements a clean, modern dark mode theme matching the main application.
"""

CALENDAR_STYLE = """
/* עיצוב הטבלה המרכזית */
QTableWidget {
    background-color: #1E1E1E;
    color: #E0E0E0;
    gridline-color: #333333;
    border: 1px solid #333333;
    border-radius: 4px;
    font-size: 14px;
}

/* עיצוב התאים בטבלה */
QTableWidget::item {
    padding: 5px;
    border-bottom: 1px solid #2A2A2A;
}

/* כשלוחצים או בוחרים תא */
QTableWidget::item:selected {
    background-color: #2D5A88;
    color: white;
}

/* עיצוב הכותרות (הימים / השעות) */
QHeaderView::section {
    background-color: #252526;
    color: #CCCCCC;
    font-weight: bold;
    border: 1px solid #333333;
    padding: 6px;
}

/* פס גלילה אנכי */
QScrollBar:vertical {
    border: none;
    background: #1E1E1E;
    width: 14px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background: #555555;
    min-height: 20px;
    border-radius: 7px;
}

QScrollBar::handle:vertical:hover {
    background: #666666;
}

/* פס גלילה אופקי */
QScrollBar:horizontal {
    border: none;
    background: #1E1E1E;
    height: 14px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:horizontal {
    background: #555555;
    min-width: 20px;
    border-radius: 7px;
}

QScrollBar::handle:horizontal:hover {
    background: #666666;
}
"""