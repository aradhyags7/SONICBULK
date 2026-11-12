"""Design tokens and reusable stylesheets for the editorial light aesthetic."""

from __future__ import annotations

# Colors matching the design mockup images exactly
COLOR_CANVAS = "#e4e8dc"
COLOR_SIDEBAR = "#111a14"
COLOR_SIDEBAR_BORDER = "#1b261d"
COLOR_SIDEBAR_TEXT_MUTED = "#7b8f80"
COLOR_LIME = "#bef224"
COLOR_LIME_HOVER = "#b0e41b"
COLOR_LIME_PRESSED = "#9ecc12"
COLOR_TEXT_DARK = "#111813"
COLOR_TEXT_MUTED = "#556052"
COLOR_TEXT_UPPERCASE = "#657367"
COLOR_CARD_BG = "#ffffff"
COLOR_CARD_BORDER = "#d8ddcf"
COLOR_DARK_HERO = "#131e16"
COLOR_PEACH_BG = "#fde6d2"
COLOR_PEACH_TEXT = "#a14a0f"
COLOR_NOTICE_BG = "#eff7a6"
COLOR_NOTICE_BORDER = "#e1ed8c"
COLOR_NOTICE_TEXT = "#333f20"

# Button Stylesheets
LIME_BUTTON_STYLE = f"""
QPushButton {{
    background-color: {COLOR_LIME};
    color: {COLOR_TEXT_DARK};
    font-size: 14px;
    font-weight: 700;
    border: none;
    border-radius: 10px;
    padding: 10px 24px;
}}
QPushButton:hover {{
    background-color: {COLOR_LIME_HOVER};
}}
QPushButton:pressed {{
    background-color: {COLOR_LIME_PRESSED};
}}
QPushButton:disabled {{
    background-color: #dbe4be;
    color: #788265;
}}
"""

LIME_PILL_BUTTON_STYLE = f"""
QPushButton {{
    background-color: {COLOR_LIME};
    color: {COLOR_TEXT_DARK};
    font-size: 14px;
    font-weight: 700;
    border: none;
    border-radius: 20px;
    padding: 10px 26px;
}}
QPushButton:hover {{
    background-color: {COLOR_LIME_HOVER};
}}
QPushButton:pressed {{
    background-color: {COLOR_LIME_PRESSED};
}}
QPushButton:disabled {{
    background-color: #dbe4be;
    color: #788265;
}}
"""

SECONDARY_BUTTON_STYLE = f"""
QPushButton {{
    background-color: #ffffff;
    color: {COLOR_TEXT_DARK};
    font-size: 13px;
    font-weight: 600;
    border: 1px solid {COLOR_TEXT_DARK};
    border-radius: 8px;
    padding: 7px 18px;
}}
QPushButton:hover {{
    background-color: #f2f5ed;
}}
QPushButton:pressed {{
    background-color: #e2e6dc;
}}
QPushButton:disabled {{
    background-color: #f5f5f5;
    color: #a0a0a0;
    border-color: #cccccc;
}}
"""

SIDEBAR_STEP_INACTIVE_STYLE = f"""
QPushButton {{
    text-align: left;
    padding: 9px 16px;
    border-radius: 18px;
    border: none;
    font-size: 13px;
    font-weight: 600;
    color: {COLOR_SIDEBAR_TEXT_MUTED};
    background-color: transparent;
}}
QPushButton:hover {{
    color: #ffffff;
    background-color: #18251d;
}}
"""

SIDEBAR_STEP_ACTIVE_STYLE = f"""
QPushButton {{
    text-align: left;
    padding: 9px 16px;
    border-radius: 18px;
    border: none;
    font-size: 13px;
    font-weight: 700;
    color: {COLOR_TEXT_DARK};
    background-color: {COLOR_LIME};
}}
"""

SIDEBAR_SETTINGS_STYLE = f"""
QPushButton {{
    text-align: left;
    padding: 6px 12px;
    border: none;
    background: transparent;
    color: {COLOR_SIDEBAR_TEXT_MUTED};
    font-size: 13px;
    font-weight: 500;
}}
QPushButton:hover {{
    color: #ffffff;
}}
"""

PEACH_BADGE_STYLE = f"""
QLabel {{
    background-color: {COLOR_PEACH_BG};
    color: {COLOR_PEACH_TEXT};
    border-radius: 12px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 700;
}}
"""

# Base Window Stylesheet
LIGHT_EDITORIAL_QSS = f"""
QMainWindow, QWidget#centralWidget {{
    background-color: {COLOR_CANVAS};
    color: {COLOR_TEXT_DARK};
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
}}

/* Form inputs default styling */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: #ffffff;
    color: {COLOR_TEXT_DARK};
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
    border: 1px solid {COLOR_TEXT_DARK};
}}

/* Clean table styling */
QTableWidget {{
    background-color: #ffffff;
    color: {COLOR_TEXT_DARK};
    border: none;
    gridline-color: transparent;
    selection-background-color: #f3f5ee;
    selection-color: {COLOR_TEXT_DARK};
}}

QHeaderView::section {{
    background-color: #ffffff;
    color: {COLOR_TEXT_UPPERCASE};
    border: none;
    border-bottom: 1px solid #e5ebe2;
    padding: 8px 6px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 6px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: #cbd5e1;
    min-height: 20px;
    border-radius: 3px;
}}

QScrollBar::handle:vertical:hover {{
    background: #94a3b8;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QCheckBox {{
    spacing: 8px;
    color: {COLOR_TEXT_DARK};
    font-weight: 500;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #94a3b8;
    background: #ffffff;
}}

QCheckBox::indicator:checked {{
    background-color: {COLOR_TEXT_DARK};
    border-color: {COLOR_TEXT_DARK};
}}
"""

DARK_THEME_QSS = LIGHT_EDITORIAL_QSS
