# src/styles/input_screen_style.py

# ── Tab panel constants ───────────────────────────────────────────────────────
TAB_BAR_HEIGHT    = 52          # px — height of the tab button row
TAB_BTN_PADDING   = "14px 22px" # vertical / horizontal padding inside tab button

INPUT_SCREEN_STYLE = """
/* ── App background ─────────────────────────────────────────────────────── */
QWidget#inputScreen {
    background-color: #F8FAFC;
}

/* ── Section card (col 1 – Data Input) ──────────────────────────────────── */
QFrame#sectionCard {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
}
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

/* ── Tab card (right panel replacing col 2 + 3) ─────────────────────────── */
QFrame#tabCard {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
}
QFrame#tabCard QWidget {
    background-color: transparent;
}

/* ── Tab bar (sits at the top of tabCard) ────────────────────────────────── */
QWidget#tabBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E5E7EB;
    border-top-left-radius:  12px;
    border-top-right-radius: 12px;
}

/* ── Inactive tab button ─────────────────────────────────────────────────── */
QPushButton#tabBtn {
    background:            transparent;
    border-left:           none;
    border-right:          none;
    border-top:            2px solid transparent;
    border-bottom:         2px solid transparent;
    color:                 #6B7280;
    font-size:             14px;
    font-weight:           500;
    padding:               14px 22px;
}
QPushButton#tabBtn:hover {
    color: #374151;
    border-bottom-color: #D1D5DB;
}

/* ── Active tab button (underline indicator) ─────────────────────────────── */
QPushButton#tabBtnActive {
    background:            transparent;
    border-left:           none;
    border-right:          none;
    border-top:            2px solid transparent;
    border-bottom:         2px solid #2563EB;
    color:                 #2563EB;
    font-size:             14px;
    font-weight:           600;
    padding:               14px 22px;
}

/* ── Tab content page wrapper ────────────────────────────────────────────── */
QWidget#tabPage {
    background: transparent;
}

/* ── Generate Schedule bottom bar ────────────────────────────────────────── */
QWidget#generateBar {
    background-color: #F1F5F9;
    border-top: 1px solid #E5E7EB;
}

QPushButton#generateBtn {
    background-color: #2563EB;
    color:            white;
    border-radius:    8px;
    padding:          10px 28px;
    font-weight:      bold;
    font-size:        14px;
    border:           none;
    min-width:        200px;
}
QPushButton#generateBtn:hover    { background-color: #1D4ED8; }
QPushButton#generateBtn:disabled { background-color: #9CA3AF; color: #F9FAFB; }

/* ── Courses table ───────────────────────────────────────────────────────── */
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
    color:            #6B7280;
    font-weight:      bold;
    padding:          12px 10px;
    border:           none;
    border-bottom:    1px solid #E5E7EB;
}
QTableWidget#coursesTable::item {
    padding:       10px;
    border-bottom: 1px solid #F3F4F6;
}

/* ── Scroll area ─────────────────────────────────────────────────────────── */
QScrollArea {
    border:           none;
    background-color: transparent;
}

/* ── Scrollbar ───────────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background:    #F1F5F9;
    width:         6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background:    #CBD5E1;
    border-radius: 3px;
    min-height:    20px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0px; }
"""
