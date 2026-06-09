import src.styles.theme as th


def type_badge_style(bg_color: str, text_color: str, border_color: str) -> str:
    return f"""
        QLabel {{
            background-color: {bg_color};
            color: {text_color};
            border: {th.BADGE_BORDER_WIDTH}px solid {border_color};
            border-radius: {th.BADGE_RADIUS}px;
            padding: {th.BADGE_PADDING_Y}px {th.BADGE_PADDING_X}px;
            font-family: {th.FONT_FAMILY};
            font-weight: {th.BADGE_FONT_WEIGHT};
            font-size: {th.BADGE_FONT_SIZE}px;
        }}
    """
