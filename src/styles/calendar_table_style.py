"""
Styles for CalendarTableWidget (EP-36 / EP-47).

Covers both INPUT mode (period selector) and OUTPUT mode (schedule viewer).
All values are plain strings / tuples — no PyQt5 imports here so the file
stays importable in headless / test environments.
"""

# ── Shared background / border colours ──────────────────────────────────────
GRID_COLOR         = "#E2E8F0"   # 1-px grid-line background of the month container
CELL_BG            = "#FFFFFF"   # default day-cell background
SEPARATOR_COLOR    = "#E2E8F0"   # vertical divider between left/right columns (INPUT)
CARD_BORDER_RADIUS = 8           # px, used in style strings

# ── OUTPUT day-number colours ─────────────────────────────────────────────────
DAY_COLOR_WEEKDAY = "#1E293B"    # Mon–Fri
DAY_COLOR_WEEKEND = "#E11D48"    # Sat / Sun
DAY_COLOR_OTHER   = "#CBD5E1"    # days that belong to adjacent months

# ── Day-name header row (row 0 of the month grid) ────────────────────────────
DAY_HEADER_WEEKDAY_COLOR = "#64748B"   # Mon–Fri column header text
# DAY_COLOR_WEEKEND is reused for Sat/Sun column headers
DAY_HEADER_BG            = "#F8FAFC"  # header cell background

# ── INPUT mode ───────────────────────────────────────────────────────────────
# Day in the selected range (but not start/end anchor)
IN_RANGE_BG      = "#EEF2FF"
IN_RANGE_TEXT    = "#4338CA"

# Start / end anchor day (filled circle)
ANCHOR_BG        = "#4338CA"
ANCHOR_TEXT      = "#FFFFFF"

# Unavailable day (user-marked)
UNAVAIL_IN_BG    = "#FEE2E2"
UNAVAIL_IN_TEXT  = "#DC2626"
UNAVAIL_IN_BORDER= "#FECACA"

# Day outside the selected range — shown but not interactive
OUT_RANGE_TEXT   = "#CBD5E1"
OUT_RANGE_BG     = "#F8FAFC"

# Day that belongs to a different month (leading/trailing cells)
OTHER_MONTH_TEXT = "#CBD5E1"
OTHER_MONTH_BG   = "#FAFAFA"

# ── OUTPUT mode ──────────────────────────────────────────────────────────────
# Required course badge (indigo)
REQ_BG     = "#EEF2FF"
REQ_TEXT   = "#4338CA"
REQ_BORDER = "#C7D2FE"

# Elective course badge (green)
ELECT_BG     = "#F0FDF4"
ELECT_TEXT   = "#15803D"
ELECT_BORDER = "#BBF7D0"

# Unavailable day badge (rose/salmon)
UNAVAIL_OUT_BG     = "#FFF1F2"
UNAVAIL_OUT_TEXT   = "#E11D48"
UNAVAIL_OUT_BORDER = "#FECDD3"

# No-exam cell day-number colour
NO_EXAM_DAY_TEXT  = "#94A3B8"

# ── Day-name header row ──────────────────────────────────────────────────────
DAY_HEADER_STYLE = """
    QLabel {
        color: #64748B;
        font-size: 11px;
        font-weight: 600;
        font-family: 'Segoe UI';
        background: transparent;
        padding: 4px 0px;
    }
"""

# ── Month title (e.g. "June 2026") ──────────────────────────────────────────
MONTH_TITLE_STYLE = """
    QLabel {
        color: #1E293B;
        font-size: 16px;
        font-weight: 700;
        font-family: 'Segoe UI';
        background: transparent;
    }
"""

# ── Navigation prev / next buttons ──────────────────────────────────────────
NAV_BTN_STYLE = """
    QPushButton {
        color: #64748B;
        background: transparent;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        font-size: 21px;
        font-weight: 600;
        padding: 4px 10px;
        min-width: 32px;
        min-height: 32px;
    }
    QPushButton:hover {
        background: #F1F5F9;
        color: #334155;
    }
    QPushButton:pressed {
        background: #E2E8F0;
    }
"""

# ── Date input fields (QDateEdit) ────────────────────────────────────────────
DATE_EDIT_STYLE = """
    QDateEdit {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        color: #1E293B;
        font-size: 13px;
        font-family: 'Segoe UI';
        padding: 6px 10px;
        min-height: 36px;
    }
    QDateEdit:focus {
        border-color: #6366F1;
        background: #FFFFFF;
    }
    QDateEdit::drop-down {
        border: none;
        width: 24px;
    }
    QDateEdit::up-button, QDateEdit::down-button {
        border: none;
    }
"""

DATE_LABEL_STYLE = """
    QLabel {
        color: #475569;
        font-size: 12px;
        font-weight: 600;
        font-family: 'Segoe UI';
        background: transparent;
    }
"""

# ── Outer card container ─────────────────────────────────────────────────────
CALENDAR_CARD_STYLE = """
    QFrame#calendarCard {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
    }
"""

# ── Legend items (INPUT) ─────────────────────────────────────────────────────
INPUT_LEGEND_ITEMS = [
    ("#4338CA", "Selected dates"),
    ("#DC2626", "Unavailable days"),
]

# ── Legend items (OUTPUT) — dot-colour + label ───────────────────────────────
OUTPUT_LEGEND_ITEMS = [
    (REQ_BORDER,         "Required Course"),
    (ELECT_BORDER,       "Elective Course"),
    (UNAVAIL_OUT_BORDER, "Unavailable Day"),
    ("#CBD5E1",          "No Exam"),
]

LEGEND_DOT_STYLE_TPL = "color: {color}; font-size: 28px; background: transparent;"
LEGEND_TEXT_STYLE = """
    QLabel {
        color: #64748B;
        font-size: 22px;
        font-family: 'Segoe UI';
        background: transparent;
    }
"""

# ── OUTPUT unavailable day — red circle around the day number ────────────────
UNAVAIL_CIRCLE_BG     = "#FEE2E2"
UNAVAIL_CIRCLE_BORDER = "#FCA5A5"
UNAVAIL_CIRCLE_TEXT   = "#DC2626"

# ── SAVE button (INPUT mode) ─────────────────────────────────────────────────
SAVE_BTN_STYLE = """
    QPushButton {
        background-color: #2563EB;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 6px 24px;
        font-family: Segoe UI, sans-serif;
        font-weight: 700;
        font-size: 14px;
        min-height: 32px;
    }
    QPushButton:hover {
        background-color: #1D4ED8;
    }
    QPushButton:pressed {
        background-color: #1E40AF;
    }
    QPushButton:disabled {
        background-color: #F3F4F6;
        color: #9CA3AF;
    }
"""

# ── INPUT — gray cell backgrounds for out-of-range / other-month days ────────
CELL_DISABLED_BG = "#F1F5F9"   # light slate — used for the cell QFrame itself

# ── Output badge card styles (built dynamically) ─────────────────────────────

def _badge_style(bg: str, text: str, border: str) -> str:
    return f"""
        QFrame {{
            background: {bg};
            border: 1px solid {border};
            border-radius: 6px;
        }}
        QLabel {{
            background: transparent;
            color: {text};
        }}
    """


BADGE_REQUIRED_STYLE   = _badge_style(REQ_BG,          REQ_TEXT,          REQ_BORDER)
BADGE_ELECTIVE_STYLE   = _badge_style(ELECT_BG,        ELECT_TEXT,        ELECT_BORDER)
BADGE_UNAVAILABLE_STYLE= _badge_style(UNAVAIL_OUT_BG,  UNAVAIL_OUT_TEXT,  UNAVAIL_OUT_BORDER)
