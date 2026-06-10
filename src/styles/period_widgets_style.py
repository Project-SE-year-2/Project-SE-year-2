"""
Visual style constants for PeriodListWidget and PeriodEditorWidget.
All colours and measurements are defined here so the widget files
contain zero magic numbers or hex strings.
"""

import src.styles.theme as th

# ── Period row ────────────────────────────────────────────────────────────────

ROW_PADDING_H   = 24   # px — left/right inner padding
ROW_PADDING_V   = 24   # px — top/bottom inner padding
ROW_SPACING     = 24   # px — spacing between row columns
ROW_RADIUS      = 10   # px — border-radius of each row card
ROW_BORDER_W    = 1    # px — border width (normal)
ROW_SEL_BORDER_W = 2   # px — border width (selected)

ROW_BG_NORMAL   = "#FFFFFF"
ROW_BG_HOVER    = "#F8FAFC"
ROW_BORDER_NORMAL   = "#E5E7EB"
ROW_BORDER_SELECTED = th.PRIMARY_COLOR   # "#2563EB"

ROW_TITLE_COLOR    = th.TEXT_PRIMARY     # "#111827"
ROW_TITLE_SIZE     = 26
ROW_SUBTITLE_COLOR = th.TEXT_TERTIARY    # "#6B7280"
ROW_SUBTITLE_SIZE  = 22
ROW_DATE_COLOR     = "#374151"
ROW_DATE_SIZE      = 16
ROW_PROG_NUM_COLOR = th.TEXT_PRIMARY
ROW_PROG_NUM_SIZE  = 30
ROW_PROG_LBL_COLOR = th.TEXT_TERTIARY
ROW_PROG_LBL_SIZE  = 20

# Selection indicator
IND_SIZE        = 20    # px — fixed width/height of the indicator circle
IND_EMPTY_STYLE = (
    "border: 2px solid #D1D5DB;"
    "border-radius: 10px;"
    "background: #FFFFFF;"
)
IND_CHECKED_STYLE = (
    f"border: 2px solid {th.PRIMARY_COLOR};"
    "border-radius: 10px;"
    f"background: {th.PRIMARY_COLOR};"
    "color: #FFFFFF;"
    "font-size: 10px;"
    "font-weight: bold;"
)

# Stylesheet templates (use .format())
ROW_FRAME_STYLE_NORMAL = f"""
    QFrame[periodRow="true"] {{
        background: {ROW_BG_NORMAL};
        border: {ROW_BORDER_W}px solid {ROW_BORDER_NORMAL};
        border-radius: {ROW_RADIUS}px;
    }}
    QFrame[periodRow="true"]:hover {{
        background: {ROW_BG_HOVER};
        border-color: {th.PRIMARY_COLOR};
    }}
"""

ROW_FRAME_STYLE_SELECTED = f"""
    QFrame[periodRow="true"] {{
        background: {ROW_BG_NORMAL};
        border: {ROW_SEL_BORDER_W}px solid {ROW_BORDER_SELECTED};
        border-radius: {ROW_RADIUS}px;
    }}
"""

# ── Period list header / info panel ──────────────────────────────────────────

LIST_TITLE_SIZE  = 30
LIST_HINT_SIZE   = 24

INFO_PANEL_STYLE = f"""
    QFrame#infoPanelRow {{
        background: #EFF6FF;
        border: 1px solid #BFDBFE;
        border-radius: 8px;
    }}
"""

INFO_ICON_STYLE  = "color: #2563EB; font-size: 14px; background: transparent;"
INFO_TEXT_STYLE  = (
    "color: #1D4ED8; font-size: 12px; background: transparent;"
)

# ── Period editor header ──────────────────────────────────────────────────────

EDITOR_SECTION_TITLE_SIZE    = 17   # "EDIT EXAM PERIOD" small caps label
EDITOR_SECTION_TITLE_COLOR   = th.TEXT_TERTIARY
EDITOR_SECTION_HINT_SIZE     = 18
EDITOR_SECTION_HINT_COLOR    = th.TEXT_TERTIARY

EDITOR_PERIOD_TITLE_SIZE     = 22   # large "FALL — Aleph"
EDITOR_PERIOD_TITLE_COLOR    = th.TEXT_PRIMARY
EDITOR_PERIOD_SUBTITLE_SIZE  = 13   # "FALL 2026 — Moed A"
EDITOR_PERIOD_SUBTITLE_COLOR = th.TEXT_TERTIARY

EDITOR_DIVIDER_COLOR = th.BORDER_LIGHT
