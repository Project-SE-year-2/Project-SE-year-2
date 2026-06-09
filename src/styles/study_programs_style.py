# src/styles/study_programs_style.py
"""
Styles for the Study Programs tab two-column layout:
  Left  – program list (search + filter, rows, selected panel)
  Right – courses table with pagination
"""

STUDY_PROGRAMS_STYLE = """

/* ── Programs panel header ───────────────────────────────────────────────── */
QLabel#programsPanelTitle {
    color:       #111827;
    font-size:   16px;
    font-weight: 700;
}
QLabel#programsPanelSubtitle {
    color:     #6B7280;
    font-size: 13px;
}
QLabel#programsFoundLabel {
    color:     #6B7280;
    font-size: 13px;
}

/* ── Search bar ──────────────────────────────────────────────────────────── */
QLineEdit#programSearchInput {
    background-color: #FFFFFF;
    border:           1px solid #E5E7EB;
    border-radius:    8px;
    padding:          7px 12px;
    font-size:        13px;
    color:            #111827;
    min-height:       34px;
}
QLineEdit#programSearchInput:focus {
    border-color: #2563EB;
}

/* ── Program list scroll area ────────────────────────────────────────────── */
QScrollArea#programScrollArea {
    border:           none;
    background:       transparent;
}
QScrollBar:vertical {
    background:    #F1F5F9;
    width:         5px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background:    #CBD5E1;
    border-radius: 3px;
    min-height:    20px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0px; }

/* ── Program row (normal) ────────────────────────────────────────────────── */
QWidget#programRow {
    background-color: #FFFFFF;
    border:           1px solid transparent;
    border-radius:    10px;
}

/* ── Program row (currently viewed — blue border + light blue bg) ────────── */
QWidget#programRowViewed {
    background-color: #EFF6FF;
    border:           1px solid #BFDBFE;
    border-radius:    10px;
}

/* ── "+ Add" button inside program row ───────────────────────────────────── */
QPushButton#addBtn {
    background-color: #2563EB;
    color:            #FFFFFF;
    border:           none;
    border-radius:    7px;
    padding:          5px 12px;
    font-size:        12px;
    font-weight:      600;
    min-width:        70px;
    min-height:       28px;
}
QPushButton#addBtn:hover {
    background-color: #1D4ED8;
}
QPushButton#addBtn:disabled {
    background-color: #93C5FD;
    color:            #FFFFFF;
}

/* ── "- Remove" button when program is selected for generation ───────────── */
QPushButton#addBtnSelected {
    background-color: #DC2626;
    color:            #FFFFFF;
    border:           none;
    border-radius:    7px;
    padding:          5px 12px;
    font-size:        12px;
    font-weight:      600;
    min-width:        70px;
    min-height:       28px;
}
QPushButton#addBtnSelected:hover {
    background-color: #B91C1C;
}

/* ── Course count label inside program row ───────────────────────────────── */
QLabel#courseCountLabel {
    color:     #6B7280;
    font-size: 12px;
}

/* ── Selected Programs section title ─────────────────────────────────────── */
QLabel#selectedPanelTitle {
    color:       #2563EB;
    font-size:   13px;
    font-weight: 600;
}

/* ══════════════════════════ COURSES TABLE (right) ══════════════════════════ */

/* ── Section header ──────────────────────────────────────────────────────── */
QLabel#coursesTableTitle {
    color:       #111827;
    font-size:   16px;
    font-weight: 700;
}
QLabel#coursesFoundLabel {
    color:     #6B7280;
    font-size: 13px;
}

/* ── Table ───────────────────────────────────────────────────────────────── */
QTableWidget#coursesTable {
    background-color: #FFFFFF;
    border:           1px solid #E5E7EB;
    border-radius:    10px;
    gridline-color:   #F3F4F6;
    selection-background-color: #EFF6FF;
    selection-color:  #111827;
    font-size:        13px;
    color:            #374151;
    outline:          none;
}
QTableWidget#coursesTable::item {
    padding:       10px 10px;
    border-bottom: 1px solid #F3F4F6;
}
QTableWidget#coursesTable::item:selected {
    background-color: #EFF6FF;
    color:            #111827;
}
QHeaderView::section {
    background-color: #F9FAFB;
    color:            #6B7280;
    font-weight:      600;
    font-size:        12px;
    padding:          10px 10px;
    border:           none;
    border-bottom:    1px solid #E5E7EB;
}

/* ── Type badge labels inside table cells ────────────────────────────────── */
QLabel#typeBadgeObligatory {
    background-color: #EEF2FF;
    color:            #4338CA;
    border:           1px solid #C7D2FE;
    border-radius:    5px;
    padding:          3px 10px;
    font-size:        11px;
    font-weight:      600;
}
QLabel#typeBadgeElective {
    background-color: #FFFBEB;
    color:            #92400E;
    border:           1px solid #FDE68A;
    border-radius:    5px;
    padding:          3px 10px;
    font-size:        11px;
    font-weight:      600;
}

/* ── Pagination ──────────────────────────────────────────────────────────── */
QPushButton#pageNavBtn {
    background-color: #FFFFFF;
    border:           1px solid #E5E7EB;
    border-radius:    6px;
    color:            #374151;
    font-size:        14px;
    min-width:        32px;
    min-height:       32px;
    padding:          0 6px;
}
QPushButton#pageNavBtn:hover    { background-color: #F3F4F6; }
QPushButton#pageNavBtn:disabled { color: #D1D5DB; border-color: #F3F4F6; }

QPushButton#pageNumBtn {
    background-color: transparent;
    border:           1px solid transparent;
    border-radius:    6px;
    color:            #6B7280;
    font-size:        13px;
    min-width:        32px;
    min-height:       32px;
    padding:          0 4px;
}
QPushButton#pageNumBtn:hover { background-color: #F3F4F6; }

QPushButton#pageNumBtnActive {
    background-color: #2563EB;
    border:           none;
    border-radius:    6px;
    color:            #FFFFFF;
    font-size:        13px;
    font-weight:      600;
    min-width:        32px;
    min-height:       32px;
    padding:          0 4px;
}

QLabel#paginationInfoLabel {
    color:     #6B7280;
    font-size: 13px;
}
"""
