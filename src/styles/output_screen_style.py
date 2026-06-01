OUTPUT_SCREEN_STYLE = """
/* Main dark background for the outer screen */
QWidget#mainContainer {
    background-color: #050505; 
}

/* The inner card holding the calendar */
QFrame#cardContainer {
    background-color: #0F172A; 
    border: 1px solid #1E293B;
    border-radius: 16px;
}

/* Titles - INCREASED SIZES */
QLabel#mainTitle {
    color: #F9FAFB;
    font-size: 32px; 
    font-weight: 900;
}

QLabel#monthTitle {
    color: #F9FAFB;
    font-size: 38px; 
    font-weight: 800;
}

/* Back Button */
QPushButton#backBtn {
    background-color: transparent;
    color: #F9FAFB;
    border: 1px solid #374151;
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 16px;
    font-weight: bold;
}
QPushButton#backBtn:hover { background-color: #1F2937; }

/* Primary Button (Download) */
QPushButton#primaryBtn {
    background-color: #4F46E5;
    color: white;
    border-radius: 8px;
    padding: 12px 24px;
    font-weight: bold;
    font-size: 16px;
}
QPushButton#primaryBtn:hover { background-color: #4338CA; }

/* Schedule Navigation Buttons (Text + Icon) */
QPushButton#navTextBtn {
    background-color: transparent;
    border: 1px solid #374151;
    border-radius: 8px;
    color: #F9FAFB;
    font-weight: bold;
    font-size: 16px;
    padding: 10px 20px;
}
QPushButton#navTextBtn:hover { background-color: #1F2937; }

/* Small Square Navigation Buttons (Arrows only) */
QPushButton#iconBtn {
    background-color: transparent;
    border: 1px solid #374151;
    border-radius: 8px;
    color: #F9FAFB;
    font-weight: bold;
    font-size: 20px;
}
QPushButton#iconBtn:hover { background-color: #1F2937; }

/* Pagination Text */
QLabel#paginationText {
    color: #D1D5DB;
    font-weight: bold;
    font-size: 16px;
}

/* Segmented Control (Month / Week / List) */
QFrame#segmentedControl {
    background-color: #0B1121;
    border: 1px solid #1E293B;
    border-radius: 8px;
}
QPushButton#segBtnActive {
    background-color: #4F46E5;
    color: white;
    border-radius: 6px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: bold;
}
QPushButton#segBtnInactive {
    background-color: transparent;
    color: #9CA3AF;
    border-radius: 6px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: bold;
}
"""