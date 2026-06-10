"""
Style definitions for DayDetailDialog (multi-exam day popup).

Light-theme card that floats over the dark calendar. All colors are
self-contained here because they belong to a light sub-surface, not to
the app's main dark palette (which lives in theme.py).
"""

# ── Light card surface ────────────────────────────────────────────────
CARD_BG            = "#FFFFFF"
CARD_BORDER        = "#E2E8F0"
CARD_BORDER_RADIUS = "16px"

CARD_STYLE = f"""
    QFrame#dialogCard {{
        background-color: {CARD_BG};
        border: 1px solid {CARD_BORDER};
        border-radius: {CARD_BORDER_RADIUS};
    }}
"""

# ── Title  "Exams on DD/MM/YYYY" ─────────────────────────────────────
TITLE_STYLE = (
    "color: #1E293B; font-size: 21px; font-weight: 700; background: transparent;"
)

# ── Close button  ✕ ──────────────────────────────────────────────────
CLOSE_BTN_STYLE = """
    QPushButton {
        background: transparent;
        color: #94A3B8;
        border: none;
        font-size: 21px;
        border-radius: 4px;
    }
    QPushButton:hover {
        background: #F1F5F9;
        color: #475569;
    }
"""

# ── Exam row card ─────────────────────────────────────────────────────
EXAM_ROW_BG            = "#FFFFFF"
EXAM_ROW_BORDER        = "#E2E8F0"
EXAM_ROW_BORDER_RADIUS = "10px"

EXAM_ROW_REQUIRED_BORDER = "#4338CA"   # indigo
EXAM_ROW_ELECTIVE_BORDER = "#16A34A"   # green


def exam_row_style(border_color: str) -> str:
    """QSS for an exam-row QFrame (no coloured border)."""
    return (
        f"QFrame {{"
        f" background: {EXAM_ROW_BG};"
        f" border: none;"
        f" border-radius: {EXAM_ROW_BORDER_RADIUS};"
        f"}}"
    )


# ── Course code  (bold, type-coloured, same line as name) ────────────
COURSE_CODE_REQUIRED_STYLE = (
    "color: #4338CA; font-size: 17px; font-weight: 700; background: transparent;"
)
COURSE_CODE_ELECTIVE_STYLE = (
    "color: #16A34A; font-size: 17px; font-weight: 700; background: transparent;"
)

# ── Course name  (gray, same line as code) ────────────────────────────
COURSE_NAME_INLINE_STYLE = (
    "color: #64748B; font-size: 17px; font-weight: 400; background: transparent;"
)

# ── Mini type-badge chip  (right of top row) ─────────────────────────
def _mini_badge(bg: str, text_color: str, border: str) -> str:
    return (
        f"background: {bg}; color: {text_color}; border: 1px solid {border};"
        " border-radius: 6px; padding: 2px 13px;"
        " font-size: 15px; font-weight: 600;"
    )


MINI_BADGE_REQUIRED_STYLE = _mini_badge("#EEF2FF", "#4338CA", "#C7D2FE")
MINI_BADGE_ELECTIVE_STYLE = _mini_badge("#F0FDF4", "#16A34A", "#BBF7D0")

# ── "Programs Affected (N)"  header line ─────────────────────────────
PROGRAMS_COUNT_STYLE = (
    "color: #94A3B8; font-size: 15px; font-weight: 500; background: transparent;"
)

# ── Toggle arrow  ▲ / ▼ ──────────────────────────────────────────────
TOGGLE_ARROW_STYLE = (
    "color: #94A3B8; font-size: 15px; background: transparent;"
)

# ── Bullet program line  "• Full Name (AB)" ───────────────────────────
PROGRAM_BULLET_STYLE = (
    "color: #64748B; font-size: 15px; font-weight: 400; background: transparent;"
)

# ── Abbreviation on the right  "AB" ──────────────────────────────────
PROGRAM_ABBR_RIGHT_STYLE = (
    "color: #94A3B8; font-size: 15px; font-weight: 500; background: transparent;"
)

# ── Thin gap between exam rows ────────────────────────────────────────
ROW_DIVIDER_STYLE = "background: transparent; border: none;"

# ── Footer  "N exams on this day" (no icon) ──────────────────────────
FOOTER_STYLE = (
    "color: #4338CA; font-size: 16px; font-weight: 600; background: transparent;"
)

# kept for backward compat with old tests
PROGRAMS_STYLE = PROGRAMS_COUNT_STYLE
COURSE_NAME_STYLE = COURSE_NAME_INLINE_STYLE
