"""
Style definitions for EditExamDialog (single-exam edit popup).

Light-theme card that floats over the dark calendar.  Extends the same
visual language as DayDetailDialog but adds section headings, chip pills,
a table grid, and primary/secondary action buttons.

In edit mode the dialog is displayed at a larger fixed size (700 × 680 px)
and positioned to the right of the day-list panel.
"""

# ── Edit-mode sizing ─────────────────────────────────────────────────
EDIT_DIALOG_MIN_WIDTH  = 700
EDIT_DIALOG_MIN_HEIGHT = 500
EDIT_DIALOG_MAX_WIDTH  = 800

# ── Card surface (same as DayDetailDialog) ───────────────────────────
CARD_BG            = "#FFFFFF"
CARD_BORDER        = "#E2E8F0"
CARD_BORDER_RADIUS = "16px"

CARD_STYLE = f"""
    QFrame#editExamCard {{
        background-color: {CARD_BG};
        border: 1px solid {CARD_BORDER};
        border-radius: {CARD_BORDER_RADIUS};
    }}
"""

# ── Header ────────────────────────────────────────────────────────────
DIALOG_TITLE_STYLE = (
    "color: #1E293B; font-size: 18px; font-weight: 700; background: transparent;"
)

CLOSE_BTN_STYLE = """
    QPushButton {
        background: transparent;
        color: #94A3B8;
        border: none;
        font-size: 18px;
        border-radius: 4px;
    }
    QPushButton:hover {
        background: #F1F5F9;
        color: #475569;
    }
"""

# ── Course info area ──────────────────────────────────────────────────
TIME_DOT_STYLE = "color: #22C55E; font-size: 14px; background: transparent;"

COURSE_TIME_STYLE = (
    "color: #334155; font-size: 14px; font-weight: 600; background: transparent;"
)

COURSE_NAME_STYLE = (
    "color: #0F172A; font-size: 16px; font-weight: 700; background: transparent;"
)

COURSE_META_STYLE = (
    "color: #64748B; font-size: 13px; font-weight: 400; background: transparent;"
)

VIEW_IN_DAY_BTN_STYLE = """
    QPushButton {
        background: transparent;
        color: #4338CA;
        border: 1.5px solid #C7D2FE;
        border-radius: 8px;
        padding: 4px 10px;
        font-size: 13px;
        font-weight: 600;
    }
    QPushButton:hover {
        background: #EEF2FF;
    }
"""

def _type_badge(bg: str, text_color: str, border: str) -> str:
    return (
        f"background: {bg}; color: {text_color}; border: 1px solid {border};"
        " border-radius: 6px; padding: 2px 10px;"
        " font-size: 13px; font-weight: 600;"
    )

TYPE_BADGE_REQUIRED_STYLE = _type_badge("#EEF2FF", "#4338CA", "#C7D2FE")
TYPE_BADGE_ELECTIVE_STYLE = _type_badge("#F0FDF4", "#16A34A", "#BBF7D0")

# ── Section headings ──────────────────────────────────────────────────
SECTION_TITLE_STYLE = (
    "color: #1E293B; font-size: 15px; font-weight: 700; background: transparent;"
)

FIELD_LABEL_STYLE = (
    "color: #64748B; font-size: 13px; font-weight: 500; background: transparent;"
)

# ── Date edit + combobox ──────────────────────────────────────────────
DATE_EDIT_STYLE = """
    QDateEdit {
        background: #F8FAFC;
        color: #1E293B;
        border: 1.5px solid #CBD5E1;
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 14px;
    }
    QDateEdit:focus {
        border-color: #818CF8;
    }
    QDateEdit::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border-left: 1px solid #CBD5E1;
    }
"""

COMBO_STYLE = """
    QComboBox {
        background: #F8FAFC;
        color: #1E293B;
        border: 1.5px solid #CBD5E1;
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 14px;
    }
    QComboBox:focus {
        border-color: #818CF8;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border-left: 1px solid #CBD5E1;
    }
    QComboBox QAbstractItemView {
        background: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 6px;
        color: #1E293B;
        selection-background-color: #EEF2FF;
    }
"""

# ── Room chips ────────────────────────────────────────────────────────
ASSIGNED_ROOMS_LABEL_STYLE = (
    "color: #64748B; font-size: 13px; font-weight: 500; background: transparent;"
)

CHIP_STYLE = """
    QFrame {
        background: #EEF2FF;
        border: 1px solid #C7D2FE;
        border-radius: 14px;
    }
"""

CHIP_LABEL_STYLE = "color: #4338CA; font-size: 13px; font-weight: 600; background: transparent;"

CHIP_REMOVE_STYLE = """
    QPushButton {
        background: transparent;
        color: #818CF8;
        border: none;
        font-size: 12px;
        font-weight: 700;
        padding: 0px 2px;
    }
    QPushButton:hover {
        color: #4338CA;
    }
"""

CLEAR_ALL_BTN_STYLE = """
    QPushButton {
        background: transparent;
        color: #94A3B8;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 4px 10px;
        font-size: 13px;
    }
    QPushButton:hover {
        color: #475569;
        background: #F8FAFC;
    }
"""

# ── Available rooms table ─────────────────────────────────────────────
AVAIL_ROOMS_LABEL_STYLE = (
    "color: #64748B; font-size: 13px; font-weight: 500; background: transparent;"
)

SEARCH_STYLE = """
    QLineEdit {
        background: #F8FAFC;
        color: #1E293B;
        border: 1.5px solid #E2E8F0;
        border-radius: 8px;
        padding: 5px 10px;
        font-size: 13px;
    }
    QLineEdit:focus {
        border-color: #818CF8;
    }
"""

FILTER_COMBO_STYLE = """
    QComboBox {
        background: #F8FAFC;
        color: #475569;
        border: 1.5px solid #E2E8F0;
        border-radius: 8px;
        padding: 5px 10px;
        font-size: 13px;
        min-width: 110px;
    }
    QComboBox::drop-down { width: 20px; border-left: 1px solid #E2E8F0; }
    QComboBox QAbstractItemView {
        background: #FFFFFF;
        border: 1px solid #CBD5E1;
        color: #1E293B;
        selection-background-color: #EEF2FF;
    }
"""

TABLE_STYLE = """
    QTableWidget {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        gridline-color: #F1F5F9;
        font-size: 13px;
        color: #334155;
    }
    QHeaderView::section {
        background: #F8FAFC;
        color: #94A3B8;
        font-size: 12px;
        font-weight: 600;
        border: none;
        border-bottom: 1px solid #E2E8F0;
        padding: 6px 8px;
    }
    QTableWidget::item {
        padding: 6px 8px;
        border: none;
    }
    QTableWidget::item:selected {
        background: #EEF2FF;
        color: #4338CA;
    }
"""

ASSIGN_BTN_STYLE = """
    QPushButton {
        background: #FFFFFF;
        color: #4338CA;
        border: 1.5px solid #C7D2FE;
        border-radius: 6px;
        padding: 3px 10px;
        font-size: 12px;
        font-weight: 600;
    }
    QPushButton:hover {
        background: #EEF2FF;
    }
"""

ASSIGNED_BTN_STYLE = """
    QPushButton {
        background: #DCFCE7;
        color: #16A34A;
        border: 1.5px solid #86EFAC;
        border-radius: 6px;
        padding: 3px 10px;
        font-size: 12px;
        font-weight: 600;
    }
"""

CAPACITY_HINT_STYLE = (
    "color: #94A3B8; font-size: 12px; font-weight: 400; background: transparent;"
)

# ── Thin horizontal rule between sections ─────────────────────────────
SEPARATOR_STYLE = (
    "background: #E2E8F0; border: none; max-height: 1px;"
)

# ── Edit-mode notice banner ───────────────────────────────────────────
NOTICE_STYLE = """
    QLabel {
        background: #F0F9FF;
        color: #0369A1;
        border: 1px solid #BAE6FD;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 12px;
    }
"""

# ── Footer buttons ────────────────────────────────────────────────────
CANCEL_BTN_STYLE = """
    QPushButton {
        background: #FFFFFF;
        color: #475569;
        border: 1.5px solid #CBD5E1;
        border-radius: 10px;
        padding: 10px 24px;
        font-size: 14px;
        font-weight: 600;
    }
    QPushButton:hover {
        background: #F8FAFC;
    }
"""

SAVE_BTN_STYLE = """
    QPushButton {
        background: #4338CA;
        color: #FFFFFF;
        border: none;
        border-radius: 10px;
        padding: 10px 24px;
        font-size: 14px;
        font-weight: 700;
    }
    QPushButton:hover {
        background: #3730A3;
    }
    QPushButton:disabled {
        background: #C7D2FE;
        color: #E0E7FF;
    }
"""
