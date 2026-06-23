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
DRAG_HANDLE = "color: #CBD5E1; font-size: 16px;"

# ── Row description text ──────────────────────────────────────────────────────
# Dark text for the metric description sentence inside each row.
DESCRIPTION_LABEL = "color: #1E293B; font-size: 12px;"

# ── Section title (above the list) ───────────────────────────────────────────
# Bold, slightly larger than the description text.
TITLE_LABEL = "font-weight: bold; font-size: 14px; color: #1E293B;"

# ── Subtitle / instruction line (below the title) ────────────────────────────
# Smaller and grey — secondary information that doesn't compete with the title.
SUBTITLE_LABEL = "font-size: 11px; color: #64748B;"
