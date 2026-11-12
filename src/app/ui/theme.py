"""Refined editorial aesthetic stylesheet matching custom design with left sidebar."""

LIGHT_EDITORIAL_QSS = """
QMainWindow, QWidget#centralWidget {
    background-color: #e6e9e1;
    color: #111813;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
}

/* Sidebar Styles */
QWidget#sidebarWidget {
    background-color: #121b15;
    border-right: 1px solid #1c2921;
}

QLabel#sidebarLogo {
    color: #ffffff;
    font-size: 20px;
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -0.5px;
}

QPushButton#sidebarStepBtn {
    text-align: left;
    padding: 8px 14px;
    border-radius: 18px;
    border: none;
    font-size: 13px;
    font-weight: 600;
    color: #8e9f94;
    background-color: transparent;
}

QPushButton#sidebarStepBtn:hover {
    color: #ffffff;
    background-color: #1a261f;
}

QPushButton#sidebarStepBtn[active="true"] {
    background-color: #c8f53c;
    color: #111813;
    font-weight: 700;
}

QPushButton#sidebarSettingsBtn {
    text-align: left;
    padding: 6px 14px;
    border: none;
    background: transparent;
    color: #8e9f94;
    font-size: 13px;
    font-weight: 500;
}

QPushButton#sidebarSettingsBtn:hover {
    color: #ffffff;
}

/* Standard Buttons */
QPushButton {
    background-color: #ffffff;
    color: #111813;
    border: 1px solid #111813;
    border-radius: 8px;
    padding: 7px 16px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #f3f5ee;
}

QPushButton:pressed {
    background-color: #e2e5dc;
}

QPushButton:disabled {
    background-color: #f1f3ed;
    color: #9ca3af;
    border-color: #d1d5db;
}

/* Primary Lime Green Button */
QPushButton#primaryLimeBtn {
    background-color: #c8f53c;
    color: #111813;
    border: none;
    border-radius: 8px;
    padding: 9px 20px;
    font-weight: 700;
    font-size: 13px;
}

QPushButton#primaryLimeBtn:hover {
    background-color: #b8e62f;
}

QPushButton#primaryLimeBtn:pressed {
    background-color: #a8d625;
}

QPushButton#primaryLimeBtn:disabled {
    background-color: #dbe4be;
    color: #788265;
}

/* Secondary Button */
QPushButton#secondaryButton {
    background-color: #ffffff;
    color: #111813;
    border: 1px solid #111813;
    border-radius: 8px;
    padding: 7px 16px;
}

QPushButton#secondaryButton:hover {
    background-color: #f3f5ee;
}

/* White Card Containers */
QFrame#whiteCard {
    background-color: #ffffff;
    border: 1px solid #d8ddcf;
    border-radius: 16px;
}

/* Dark Hero Card */
QFrame#darkHeroCard {
    background-color: #141f17;
    border-radius: 16px;
    border: none;
}

/* Form Inputs */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #ffffff;
    color: #111813;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #111813;
}

/* Clean White Tables */
QTableWidget {
    background-color: #ffffff;
    color: #111813;
    border: none;
    gridline-color: transparent;
    selection-background-color: #f3f5ee;
    selection-color: #111813;
}

QHeaderView::section {
    background-color: #ffffff;
    color: #64748b;
    border: none;
    border-bottom: 1px solid #e2e8f0;
    padding: 10px 8px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    min-height: 20px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
    color: #111813;
    font-weight: 500;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #94a3b8;
    background: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #111813;
    border-color: #111813;
    image: none;
}
"""

DARK_THEME_QSS = LIGHT_EDITORIAL_QSS  # Default to the custom design
