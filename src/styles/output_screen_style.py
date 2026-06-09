"""
Styles for the Output Screen (light theme matching the design).

All colours here are light-theme — the output screen uses a white card on a
very-light-gray background, intentionally different from the dark input screen.
"""

# ── Screen / card backgrounds ────────────────────────────────────────────────
SCREEN_BG          = "#F5F7FB"   # outer page background (design spec)
CARD_BG            = "#FFFFFF"   # white card
CARD_BORDER        = "#E2E8F0"
CARD_RADIUS        = 16          # px

# ── Semester header (inside the card) ───────────────────────────────────────
SEMESTER_TITLE_COLOR    = "#1E293B"   # "FALL 2026"
SEMESTER_TITLE_SIZE     = 22
SEMESTER_SUBTITLE_COLOR = "#64748B"   # "September 2026 – December 2026"
SEMESTER_SUBTITLE_SIZE  = 12
SEMESTER_ICON_COLOR     = "#4338CA"   # leaf / feather icon colour

# ── Schedule navigator (‹ N of M ›) ─────────────────────────────────────────
NAV_ARROW_STYLE = """
QPushButton#navArrowBtn {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    color: #475569;
    font-size: 16px;
    font-weight: 600;
    min-width: 36px;
    min-height: 36px;
}
QPushButton#navArrowBtn:hover  { background: #F1F5F9; }
QPushButton#navArrowBtn:pressed { background: #E2E8F0; }
QPushButton#navArrowBtn:disabled { color: #CBD5E1; border-color: #F1F5F9; }
"""

NAV_COUNTER_STYLE = """
QLabel#navCounter {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    color: #1E293B;
    font-size: 13px;
    font-weight: 600;
    padding: 4px 14px;
    min-height: 36px;
}
"""

# ── Top toolbar (Back / Download) ────────────────────────────────────────────
BACK_BTN_STYLE = """
QPushButton#backBtn {
    background: transparent;
    color: #475569;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#backBtn:hover  { background: #F1F5F9; }
QPushButton#backBtn:pressed { background: #E2E8F0; }
"""

DOWNLOAD_BTN_STYLE = """
QPushButton#downloadBtn {
    background: #4338CA;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 700;
}
QPushButton#downloadBtn:hover  { background: #3730A3; }
QPushButton#downloadBtn:pressed { background: #312E81; }
"""

# ── Full stylesheet assembled (applied on the screen widget) ─────────────────
OUTPUT_SCREEN_STYLE = f"""
QWidget#outputScreen {{
    background: {SCREEN_BG};
}}

QFrame#outputCard {{
    background: {CARD_BG};
    border: 1px solid {CARD_BORDER};
    border-radius: {CARD_RADIUS}px;
}}

QFrame#monthCard {{
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
}}

/* Semester tab cards (normal state is set inline; only override disabled here) */
QFrame#semTab[disabled="true"] {{
    background: #F9FAFB;
    border: 1.5px solid #E5E7EB;
    border-radius: 14px;
}}

QLabel#semesterTitle {{
    color: {SEMESTER_TITLE_COLOR};
    font-size: {SEMESTER_TITLE_SIZE}px;
    font-weight: 800;
    background: transparent;
}}

QLabel#semesterSubtitle {{
    color: {SEMESTER_SUBTITLE_COLOR};
    font-size: {SEMESTER_SUBTITLE_SIZE}px;
    font-weight: 400;
    background: transparent;
}}

QPushButton#backBtn {{
    background: transparent;
    color: #475569;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#backBtn:hover  {{ background: #F1F5F9; }}
QPushButton#backBtn:pressed {{ background: #E2E8F0; }}

QPushButton#downloadBtn {{
    background: #4338CA;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 700;
}}
QPushButton#downloadBtn:hover  {{ background: #3730A3; }}
QPushButton#downloadBtn:pressed {{ background: #312E81; }}

QPushButton#navArrowBtn {{
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    color: #475569;
    font-size: 16px;
    font-weight: 600;
    min-width: 36px;
    min-height: 36px;
}}
QPushButton#navArrowBtn:hover  {{ background: #F1F5F9; }}
QPushButton#navArrowBtn:pressed {{ background: #E2E8F0; }}
QPushButton#navArrowBtn:disabled {{ color: #CBD5E1; border-color: #F1F5F9; }}

QLabel#navCounter {{
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    color: #1E293B;
    font-size: 13px;
    font-weight: 600;
    padding: 4px 14px;
    min-height: 36px;
}}

/* ── Moed toggle buttons (מועד א / מועד ב) ───────────────────────────── */
QPushButton#moedBtn {{
    background: #FFFFFF;
    border: 1.5px solid #CBD5E1;
    border-radius: 10px;
    color: #475569;
    font-size: 13px;
    font-weight: 600;
    padding: 6px 16px;
    min-height: 36px;
}}
QPushButton#moedBtn:hover  {{ background: #F8FAFC; border-color: #94A3B8; }}

QPushButton#moedBtnSelected {{
    background: #1E3A8A;
    border: 1.5px solid #1E3A8A;
    border-radius: 10px;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 700;
    padding: 6px 16px;
    min-height: 36px;
}}
QPushButton#moedBtnSelected:hover {{ background: #1E40AF; }}

/* ── Moed info label ─────────────────────────────────────────────────── */
QLabel#moedInfoLbl {{
    color: #64748B;
    font-size: 11px;
    font-weight: 400;
    background: transparent;
    padding: 4px 10px;
    border-left: 2px solid #E2E8F0;
}}

/* ── Back to Top button ──────────────────────────────────────────────── */
QPushButton#backToTopBtn {{
    background: transparent;
    border: none;
    color: #475569;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#backToTopBtn:hover {{ color: #1E293B; }}
"""
