# src/styles/input_screen_style.py

INPUT_SCREEN_STYLE = """
/* Main dark background */
QWidget#mainContainer {
    background-color: #050505;
}

/* Header */
QLabel#mainTitle {
    color: #F9FAFB;
    font-size: 24px;
    font-weight: 900;
    margin-left: 15px;
}
QPushButton#backBtn {
    background-color: transparent;
    color: #F9FAFB;
    border: 1px solid #374151;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 15px;
    font-weight: bold;
}
QPushButton#backBtn:hover { background-color: #1F2937; }

QPushButton#iconBtn {
    background-color: transparent;
    border: 1px solid #374151;
    border-radius: 8px;
    color: #F9FAFB;
    font-weight: bold;
    font-size: 16px;
    width: 32px;
    height: 32px;
}
QPushButton#iconBtn:hover { background-color: #1F2937; }

/* Programs List (Cards) */
QListWidget#programsList {
    background-color: transparent;
    border: none;
    outline: none;
}
QListWidget#programsList::item {
    background-color: #0B1121;
    border: 1px solid #1E293B;
    border-radius: 12px;
    color: #9CA3AF;
    padding: 20px;
    margin-bottom: 15px;
    font-size: 16px;
}
QListWidget#programsList::item:selected {
    background-color: #1E1B4B; /* Dark purple/blue tint */
    border: 2px solid #4F46E5;
    color: #E0E7FF;
}

/* Confirm Selection Button */
QPushButton#confirmBtn {
    background-color: transparent;
    color: #6366F1;
    font-size: 16px;
    font-weight: bold;
    border: none;
    padding: 10px;
}
QPushButton#confirmBtn:hover { color: #818CF8; }

/* Courses Table Area */
QLabel#programIdLabel {
    color: #F9FAFB;
    font-size: 16px;
    font-weight: bold;
}
QLabel#programIdLabel span {
    color: #6366F1;
}

QTableWidget#coursesTable {
    background-color: #0B1121;
    border: 1px solid #1E293B;
    border-radius: 12px;
    color: #D1D5DB;
    font-size: 14px;
}
QTableWidget#coursesTable QHeaderView::section {
    background-color: #0B1121;
    color: #9CA3AF;
    font-weight: bold;
    padding: 15px 10px;
    border: none;
    border-bottom: 1px solid #1F2937;
}
QTableWidget#coursesTable::item {
    padding: 10px;
    border-bottom: 1px solid #1F2937;
}

/* Generate Schedule Button */
QPushButton#generateBtn {
    background-color: #4F46E5;
    color: white;
    border-radius: 12px;
    padding: 18px;
    font-weight: bold;
    font-size: 18px;
    margin-top: 20px;
}
QPushButton#generateBtn:hover { background-color: #4338CA; }
QPushButton#generateBtn:disabled {
    background-color: #1F2937;
    color: #4B5563;
}

/* Pill Label for Table injected via code */
QLabel#typePill {
    background-color: #312E81;
    color: #A5B4FC;
    border-radius: 12px;
    padding: 6px 12px;
    font-weight: bold;
    font-size: 12px;
}

/* Scroll Area Styles */
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

"""

