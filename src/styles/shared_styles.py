"""
Shared Styles Factory.
Provides standardized CSS strings for UI components, ensuring visual consistency.
All style functions read from theme constants so a single change to theme.py
propagates automatically to every component that uses this module.
"""

import src.styles.theme as th


def get_section_label_style() -> str:
    """Muted label style used for field captions (e.g. 'Course Number')."""
    return (
        f"color: {th.TEXT_MUTED};"
        f"font-size: {th.FONT_SIZE_SM}px;"
        f"font-weight: {th.FONT_WEIGHT_MEDIUM};"
        "font-family: 'Segoe UI', sans-serif;"
    )


def get_value_label_style() -> str:
    """Bright label style used for field values."""
    return (
        f"color: {th.TEXT_PRIMARY};"
        f"font-size: {th.FONT_SIZE_MD}px;"
        f"font-weight: {th.FONT_WEIGHT_MEDIUM};"
        "font-family: 'Segoe UI', sans-serif;"
    )


def get_divider_style() -> str:
    """Thin horizontal divider line style."""
    return f"background-color: {th.BORDER_LIGHT}; border: none;"


def get_program_chip_style() -> str:
    """Small chip style used to display program names/IDs."""
    return (
        f"background-color: {th.BG_DARK_TERTIARY};"
        f"color: {th.TEXT_SECONDARY};"
        f"border: 1px solid {th.BORDER_LIGHT};"
        "border-radius: 6px;"
        "padding: 0px 10px;"
        f"font-size: {th.FONT_SIZE_SM}px;"
        f"font-weight: {th.FONT_WEIGHT_BOLD};"
        "font-family: 'Segoe UI', sans-serif;"
    )
