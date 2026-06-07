"""
Style definitions specific to DayDetailDialog.
Generic/shared styles (section labels, value labels, divider, program chips)
live in shared_styles.py and are imported from there.
Only dialog-specific styles (card surface, title, close button) are defined here.
"""

import src.styles.theme as th


# ── Card (the dialog surface) ────────────────────────────────────────
CARD_STYLE = f"""
    QFrame#dialogCard {{
        background-color: {th.BG_DARK_SECONDARY};
        border: 1px solid {th.BORDER_LIGHT};
        border-radius: 12px;
    }}
"""

# ── Title label ──────────────────────────────────────────────────────
TITLE_STYLE = (
    f"color: {th.TEXT_PRIMARY};"
    f"font-size: {th.FONT_SIZE_LG}px;"
    f"font-weight: {th.FONT_WEIGHT_BOLD};"
    "font-family: 'Segoe UI', sans-serif;"
)

# ── Close button ─────────────────────────────────────────────────────
CLOSE_BTN_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {th.TEXT_MUTED};
        border: none;
        font-size: 14px;
        border-radius: 4px;
    }}
    QPushButton:hover {{
        background-color: {th.BG_DARK_TERTIARY};
        color: {th.TEXT_PRIMARY};
    }}
"""
