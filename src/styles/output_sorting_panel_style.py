"""
Styles for the sorting panel shown on the output screen.

The widget logic lives in the ranking configuration component; this module
keeps the output-screen visual treatment separate from the settings screen.
"""

PANEL_WIDTH = 460
PANEL_MARGIN = 20
PANEL_SPACING = 12

ROW_MARGIN_H = 12
ROW_MARGIN_V = 16
ROW_SPACING = 10
HANDLE_WIDTH = 18
BADGE_SIZE = 28
BADGE_FONT_PT = 10
TEXT_BLOCK_SPACING = 4

PANEL_WIDGET = """
    QWidget#OutputSortingPanel {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
    }
"""

LIST_WIDGET = """
    QListWidget {
        border: none;
        background: transparent;
        outline: 0;
    }
    QListWidget::item {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 0px;
    }
    QListWidget::item:selected {
        background: #EEF0FE;
        border: 1px solid #D6D9FB;
    }
"""

CHECKBOX = """
    QCheckBox::indicator {
        width: 20px;
        height: 20px;
        border-radius: 4px;
        border: 2px solid #CBD5E1;
        background-color: #FFFFFF;
    }
    QCheckBox::indicator:checked {
        background-color: #4F46E5;
        border: 2px solid #4F46E5;
        image: url(none);
    }
"""

BADGE_ACTIVE = (
    "background-color: #4F46E5; color: #FFFFFF; border-radius: 14px;"
)
BADGE_INACTIVE = (
    "background-color: #F1F5F9; color: #94A3B8; border-radius: 14px;"
)

DRAG_HANDLE = "color: #CBD5E1; font-size: 18px;"
ROW_TITLE_LABEL = "color: #111827; font-size: 15px; font-weight: 700;"
DESCRIPTION_LABEL = "color: #6B7280; font-size: 13px;"

TITLE_LABEL = "font-weight: 700; font-size: 16px; color: #0F172A;"
SUBTITLE_LABEL = "font-size: 13px; color: #64748B;"

APPLY_BUTTON = """
    QPushButton {
        background-color: #4F46E5;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 15px;
        font-weight: 700;
    }
    QPushButton:hover {
        background-color: #4338CA;
    }
    QPushButton:pressed {
        background-color: #3730A3;
    }
"""
