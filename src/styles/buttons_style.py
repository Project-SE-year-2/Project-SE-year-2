import src.styles.theme as th

PRIMARY_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {th.PRIMARY_COLOR};
        color: white;
        border: none;
        border-radius: {th.BUTTON_BORDER_RADIUS}px;
        padding: {th.BUTTON_PADDING_VERTICAL_SM}px {th.BUTTON_PADDING_HORIZONTAL}px;
        font-family: {th.FONT_FAMILY};
        font-weight: {th.FONT_WEIGHT_BOLD};
        font-size: {th.FONT_SIZE_MD}px;
        min-height: {th.BUTTON_MIN_HEIGHT_SM}px;
    }}
    QPushButton:hover {{
        background-color: {th.PRIMARY_DARK};
    }}
    QPushButton:pressed {{
        background-color: {th.PRIMARY_DARKER};
    }}
    QPushButton:disabled {{
        background-color: {th.DISABLED_BG};
        color: {th.DISABLED_TEXT};
    }}
"""

SECONDARY_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {th.BUTTON_SECONDARY_BG};
        color: {th.BUTTON_SECONDARY_TEXT};
        border: 1px solid {th.BUTTON_SECONDARY_BORDER};
        border-radius: {th.BUTTON_BORDER_RADIUS}px;
        padding: {th.BUTTON_PADDING_VERTICAL_SM}px {th.BUTTON_PADDING_HORIZONTAL}px;
        font-family: {th.FONT_FAMILY};
        font-weight: {th.FONT_WEIGHT_MEDIUM};
        font-size: {th.FONT_SIZE_MD}px;
        min-height: {th.BUTTON_MIN_HEIGHT_SM}px;
    }}
    QPushButton:hover {{
        background-color: {th.BUTTON_SECONDARY_HOVER_BG};
        border-color: {th.BUTTON_SECONDARY_HOVER_BORDER};
    }}
    QPushButton:pressed {{
        background-color: {th.BUTTON_SECONDARY_PRESSED_BG};
        border-color: {th.BUTTON_SECONDARY_PRESSED_BORDER};
    }}
    QPushButton:disabled {{
        color: {th.DISABLED_TEXT};
        border-color: {th.DISABLED_BORDER};
    }}
"""

DANGER_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {th.DANGER_COLOR};
        color: white;
        border: none;
        border-radius: {th.BUTTON_BORDER_RADIUS}px;
        padding: {th.BUTTON_PADDING_VERTICAL_SM}px {th.BUTTON_PADDING_HORIZONTAL}px;
        font-family: {th.FONT_FAMILY};
        font-weight: {th.FONT_WEIGHT_BOLD};
        font-size: {th.FONT_SIZE_MD}px;
        min-height: {th.BUTTON_MIN_HEIGHT_SM}px;
    }}
    QPushButton:hover {{
        background-color: {th.DANGER_DARK};
    }}
    QPushButton:pressed {{
        background-color: {th.DANGER_DARKER};
    }}
    QPushButton:disabled {{
        background-color: {th.DISABLED_BG};
        color: {th.DISABLED_TEXT};
    }}
"""
