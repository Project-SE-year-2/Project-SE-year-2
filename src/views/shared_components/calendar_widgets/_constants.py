"""
Shared constants for the calendar sub-widgets.

Colours are imported from src.styles.calendar_table_style (single source of
truth).  Only non-colour constants (locale, day abbreviations) are defined here.
"""

from PyQt5.QtCore import QLocale

from src.styles.calendar_table_style import (  # noqa: F401  (re-exported)
    DAY_COLOR_OTHER,
    DAY_COLOR_WEEKDAY,
    DAY_COLOR_WEEKEND,
    DAY_HEADER_BG,
    DAY_HEADER_WEEKDAY_COLOR,
)

# Locale used to produce English month names ("June 2026", etc.)
EN_LOCALE = QLocale(QLocale.English, QLocale.UnitedStates)

# Day-abbreviation header row (Sun-first column order)
DAY_ABBREVS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
