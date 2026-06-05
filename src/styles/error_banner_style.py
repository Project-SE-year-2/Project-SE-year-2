import src.styles.theme as th

BANNER_MESSAGE_STYLE = (
    f"color: {th.ERROR_TEXT}; "
    f"font-family: {th.FONT_FAMILY}; "
    f"font-size: {th.FONT_SIZE_MD}px; "
    f"font-weight: {th.BANNER_FONT_WEIGHT};"
)

BANNER_DISMISS_BTN_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {th.ERROR_TEXT};
        border: none;
        font-family: {th.FONT_FAMILY};
        font-size: {th.BANNER_BTN_FONT_SIZE}px;
        font-weight: {th.BANNER_BTN_FONT_WEIGHT};
    }}
    QPushButton:hover {{
        background-color: {th.ERROR_BG};
        border-radius: {th.BANNER_BUTTON_RADIUS}px;
    }}
"""

BANNER_CONTAINER_STYLE = f"""
    ErrorBanner {{
        background-color: {th.ERROR_BG};
        border: {th.BANNER_BORDER_WIDTH}px solid {th.ERROR_BORDER};
        border-radius: {th.BANNER_BORDER_RADIUS}px;
    }}
"""


def banner_error_text(message: str) -> str:
    return f'<span style="color: {th.ICON_ERROR}; font-size: {th.ERROR_ICON_SIZE}px;">●</span>  {message}'
