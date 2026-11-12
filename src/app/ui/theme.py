"""Modern dark and light stylesheets for PySide6 UI."""

DARK_THEME_QSS = """
QMainWindow, QDialog, QWidget#centralWidget {
    background-color: #121316;
    color: #e4e6eb;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #23272e;
    background: #181a1f;
    border-radius: 8px;
}

QTabBar::tab {
    background: #1a1c22;
    color: #9ba1b0;
    padding: 10px 18px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background: #252830;
    color: #ffffff;
    font-weight: 600;
    border-bottom: 2px solid #3b82f6;
}

QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #1d4ed8;
}

QPushButton:pressed {
    background-color: #1e40af;
}

QPushButton:disabled {
    background-color: #2b303c;
    color: #6b7280;
}

QPushButton#secondaryButton {
    background-color: #252830;
    color: #e4e6eb;
    border: 1px solid #373b45;
}

QPushButton#secondaryButton:hover {
    background-color: #2f3440;
}

QPushButton#dangerButton {
    background-color: #dc2626;
    color: #ffffff;
}

QPushButton#dangerButton:hover {
    background-color: #b91c1c;
}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #1a1c22;
    color: #f3f4f6;
    border: 1px solid #2f3440;
    border-radius: 6px;
    padding: 6px 10px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #3b82f6;
}

QTableWidget {
    background-color: #181a1f;
    alternate-background-color: #14161b;
    color: #e4e6eb;
    border: 1px solid #23272e;
    border-radius: 6px;
    gridline-color: #23272e;
    selection-background-color: #1e3a8a;
    selection-color: #ffffff;
}

QHeaderView::section {
    background-color: #1e2128;
    color: #9ba1b0;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #282c34;
    font-weight: 600;
}

QProgressBar {
    background-color: #1f2229;
    border: none;
    border-radius: 5px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
}

QProgressBar::chunk {
    background-color: #3b82f6;
    border-radius: 5px;
}

QProgressBar#successChunk::chunk {
    background-color: #10b981;
}

QScrollBar:vertical {
    background: #121316;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #2f3440;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #474f61;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QCheckBox {
    color: #e4e6eb;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #373b45;
    background: #1a1c22;
}

QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #2563eb;
}

QGroupBox {
    border: 1px solid #282c34;
    border-radius: 8px;
    margin-top: 18px;
    padding-top: 14px;
    font-weight: 600;
    color: #cbd5e1;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 12px;
}
"""

