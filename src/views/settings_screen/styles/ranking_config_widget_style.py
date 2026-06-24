"""
ranking_config_widget_style.py
--------------------------------
All stylesheet strings for RankingConfigWidget and its _RowWidget rows.

Keeping styles in a separate file means the widget code stays readable
and colours/sizes can be changed here without touching logic.

PyQt5 stylesheets use the same syntax as CSS but only a subset of
CSS properties are supported.  Each constant below is a plain string
that gets passed to widget.setStyleSheet().
"""

# ── Row layout constants ──────────────────────────────────────────────────────
ROW_MARGIN_H      = 8   # left/right padding inside each row card (px)
ROW_MARGIN_V      = 10  # top/bottom padding inside each row card (px)
ROW_SPACING       = 12  # horizontal gap between row elements (px)
HANDLE_WIDTH      = 16  # fixed width of the drag-handle label (px)
BADGE_SIZE        = 28  # width and height of the circular priority badge (px)
BADGE_FONT_PT     = 10  # point size of the number inside the badge
TEXT_BLOCK_SPACING = 2  # vertical gap between title and description labels (px)

# ── List container ────────────────────────────────────────────────────────────
# Applied to the QListWidget that holds all metric rows.
# "border: none" removes the default sunken border around the list.
# "background: transparent" lets the parent widget's background show through.
# Each QListWidget::item is one row card — given a white background, a light
# border, and rounded corners to look like a card.
# The :selected state highlights the card in light blue when the user clicks it.
LIST_WIDGET = """
    QListWidget {
        border: none;
        background: transparent;
    }
    QListWidget::item {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 0px;
    }
    QListWidget::item:selected {
        background: #EFF6FF;
        border: 1px solid #93C5FD;
    }
"""

# ── Checkbox ──────────────────────────────────────────────────────────────────
# Applied to the QCheckBox inside each row.
# We style the indicator (the square box) directly because PyQt5 doesn't
# let us use a real tick image easily — instead we colour the background blue
# when checked and white when unchecked.
# border-radius: 4px makes the box slightly rounded.
CHECKBOX = """
    QCheckBox::indicator {
        width: 20px; height: 20px;
        border-radius: 4px;
        border: 2px solid #3B5BDB;
    }
    QCheckBox::indicator:checked {
        background-color: #3B5BDB;
        image: url(none);
    }
    QCheckBox::indicator:unchecked {
        background-color: #FFFFFF;
    }
"""

# ── Priority badge — active (row is checked) ──────────────────────────────────
# Blue circle with white text.
# border-radius: 14px on a 28×28 widget makes it a perfect circle
# (half of 28 = 14).
BADGE_ACTIVE = (
    "background-color: #3B5BDB; color: white; border-radius: 14px;"
)

# ── Priority badge — inactive (row is unchecked) ──────────────────────────────
# Same shape as BADGE_ACTIVE but grey, signalling "not participating in sort".
BADGE_INACTIVE = (
    "background-color: #E2E8F0; color: #94A3B8; border-radius: 14px;"
)

# ── Drag handle ───────────────────────────────────────────────────────────────
# Light grey braille-dots character used as a visual grip icon.
# font-size: 16px makes it large enough to be visible without being intrusive.
DRAG_HANDLE = "color: #64748B; font-size: 16px;"

# ── Row title text (main idea, shown large and bold) ─────────────────────────
ROW_TITLE_LABEL = "color: #1E293B; font-size: 16px; font-weight: bold;"

# ── Row description text (detail line, smaller and grey) ─────────────────────
DESCRIPTION_LABEL = "color: #64748B; font-size: 14px;"

# ── Section title (above the list) ───────────────────────────────────────────
# Bold, slightly larger than the description text.
TITLE_LABEL = "font-weight: bold; font-size: 14px; color: #1E293B;"

# ── Subtitle / instruction line (below the title) ────────────────────────────
# Smaller and grey — secondary information that doesn't compete with the title.
SUBTITLE_LABEL = "font-size: 11px; color: #64748B;"
