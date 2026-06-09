# src/styles/input_screen_style.py

INPUT_SCREEN_STYLE = """
/* App background - only targets the root InputScreen widget */
QWidget#inputScreen {
    background-color: #F8FAFC;
}

/* White card panels */
QFrame#sectionCard {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
}

/* Transparent containers inside cards so card white shows through */
QFrame#sectionCard QWidget {
    background-color: transparent;
}

QLabel#sectionTitle {
    color: #111827;
    font-size: 15px;
    font-weight: bold;
    background: transparent;
}

QLabel#sectionSubtitle {
    color: #9CA3AF;
    font-size: 12px;
    background: transparent;
}

/* Generate Schedule bottom bar */
QWidget#generateBar {
    background-color: #F1F5F9;
    border-top: 1px solid #E5E7EB;
}

QPushButton#generateBtn {
    background-color: #2563EB;
    color: white;
    border-radius: 8px;
    padding: 10px 28px;
    font-weight: bold;
    font-size: 14px;
    border: none;
    min-width: 200px;
}
QPushButton#generateBtn:hover { background-color: #1D4ED8; }
QPushButton#generateBtn:disabled {
    background-color: #9CA3AF;
    color: #F9FAFB;
}

/* Courses table */
QTableWidget#coursesTable {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    color: #374151;
    font-size: 13px;
    gridline-color: #F3F4F6;
}
QTableWidget#coursesTable QHeaderView::section {
    background-color: #F9FAFB;
    color: #6B7280;
    font-weight: bold;
    padding: 12px 10px;
    border: none;
    border-bottom: 1px solid #E5E7EB;
}
QTableWidget#coursesTable::item {
    padding: 10px;
    border-bottom: 1px solid #F3F4F6;
}

/* Scroll area */
QScrollArea {
    border: none;
    background-color: transparent;
}

/* Scrollbar */
QScrollBar:vertical {
    background: #F1F5F9;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""