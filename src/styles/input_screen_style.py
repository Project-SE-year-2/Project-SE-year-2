# src/styles/input_screen_style.py

INPUT_SCREEN_STYLE = """
/* App background */
QWidget {
    background-color: #F8FAFC;
    color: #111827;
    font-family: "Segoe UI", sans-serif;
}

/* White card panels */
QFrame#sectionCard {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
}

/* Section header numbers */
QLabel#sectionNumber {
    background-color: #2563EB;
    color: #FFFFFF;
    border-radius: 12px;
    font-size: 14px;
    font-weight: bold;
    min-width: 24px;
    max-width: 24px;
    min-height: 24px;
    max-height: 24px;
    qproperty-alignment: AlignCenter;
}

QLabel#sectionTitle {
    color: #111827;
    font-size: 16px;
    font-weight: bold;
}

QLabel#sectionSubtitle {
    color: #6B7280;
    font-size: 13px;
}

/* Programs list rows */
QListWidget#programsList {
    background-color: transparent;
    border: none;
    outline: none;
}
QListWidget#programsList::item {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    color: #374151;
    padding: 10px 14px;
    margin-bottom: 4px;
    font-size: 14px;
}
QListWidget#programsList::item:selected {
    background-color: #EFF6FF;
    border: 1.5px solid #2563EB;
    color: #1D4ED8;
}
QListWidget#programsList::item:hover {
    background-color: #F1F5F9;
}

/* Courses table */
QLabel#programIdLabel {
    color: #111827;
    font-size: 15px;
    font-weight: bold;
}

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

/* Generate Schedule bottom bar */
QWidget#generateBar {
    background-color: #F1F5F9;
    border-top: 1px solid #E5E7EB;
}

QPushButton#generateBtn {
    background-color: #2563EB;
    color: white;
    border-radius: 10px;
    padding: 14px 32px;
    font-weight: bold;
    font-size: 16px;
    border: none;
    min-width: 220px;
}
QPushButton#generateBtn:hover { background-color: #1D4ED8; }
QPushButton#generateBtn:disabled {
    background-color: #9CA3AF;
    color: #F9FAFB;
}

/* Pill / type badge */
QLabel#typePill {
    background-color: #EEF2FF;
    color: #4338CA;
    border-radius: 10px;
    padding: 4px 10px;
    font-weight: bold;
    font-size: 12px;
}

/* Scroll area */
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollArea > QWidget > QWidget {
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
