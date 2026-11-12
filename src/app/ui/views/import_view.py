"""Import screen supporting drag-and-drop file ingestion, text pasting, and folder selection."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme import (
    COLOR_CARD_BG,
    COLOR_CARD_BORDER,
    COLOR_TEXT_DARK,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_UPPERCASE,
    LIME_PILL_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
)


class DropZoneWidget(QFrame):
    """Visual drag-and-drop zone with dotted background grid and dashed rounded border."""

    def __init__(self, on_file_dropped: Callable[[Path], None], on_browse_clicked: Callable[[], None]) -> None:
        super().__init__()
        self.on_file_dropped = on_file_dropped
        self.on_browse_clicked = on_browse_clicked
        self.setAcceptDrops(True)
        self.setMinimumHeight(240)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(14)

        self.lbl_text = QLabel("Drag a playlist file here", self)
        self.lbl_text.setStyleSheet(f"color: {COLOR_TEXT_DARK}; font-size: 22px; font-weight: 800; border: none; background: transparent;")
        self.lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_browse = QPushButton("Browse file", self)
        self.btn_browse.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse.clicked.connect(self.on_browse_clicked)

        layout.addWidget(self.lbl_text)
        layout.addWidget(self.btn_browse, alignment=Qt.AlignmentFlag.AlignCenter)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        w = rect.width()
        h = rect.height()

        # Rounded rectangle background & dashed outline
        painter.setBrush(QColor("#dde2d6"))
        pen = QPen(QColor("#405043"), 1.5, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 18, 18)

        # Dot matrix pattern
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(64, 80, 67, 85))
        spacing = 16
        for x in range(24, w - 24, spacing):
            for y in range(24, h - 24, spacing):
                painter.drawEllipse(x, y, 2, 2)

    def set_selected_filename(self, filename: str) -> None:
        self.lbl_text.setText(f"Selected: {filename}")

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if urls:
            path = Path(urls[0].toLocalFile())
            self.on_file_dropped(path)


class ImportView(QWidget):
    """Primary import screen matching the editorial design."""

    def __init__(
        self,
        default_output_dir: str,
        on_parse_requested: Callable[[Path | None, str, str], None],
    ) -> None:
        super().__init__()
        self.output_dir = default_output_dir
        self.on_parse_requested = on_parse_requested
        self.selected_file_path: Path | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 36, 40, 36)
        layout.setSpacing(20)

        # Main Header Title & Subtitle
        header_box = QVBoxLayout()
        header_box.setSpacing(6)

        title = QLabel("Drop a list.\nGet a folder.", self)
        title.setStyleSheet(f"font-size: 36px; font-weight: 800; color: {COLOR_TEXT_DARK}; letter-spacing: -1px; line-height: 1.1;")
        header_box.addWidget(title)

        subtitle = QLabel("PDF, DOCX, CSV or TXT, one song per line. Everything downloads in the background.", self)
        subtitle.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 14px; font-weight: 500;")
        header_box.addWidget(subtitle)

        layout.addLayout(header_box)

        # Drag and Drop Box
        self.drop_zone = DropZoneWidget(self._handle_file_dropped, self._browse_file)
        layout.addWidget(self.drop_zone)

        # Bottom Row: Two White Cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        # Left Card: Or Paste Names
        paste_card = QFrame(self)
        paste_card.setObjectName("whiteCard")
        paste_card.setStyleSheet(f"background-color: {COLOR_CARD_BG}; border: 1px solid {COLOR_CARD_BORDER}; border-radius: 16px; padding: 14px;")
        paste_layout = QVBoxLayout(paste_card)
        paste_layout.setSpacing(8)

        lbl_paste_title = QLabel("OR PASTE NAMES", paste_card)
        lbl_paste_title.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLOR_TEXT_UPPERCASE}; letter-spacing: 0.5px; border: none; background: transparent;")
        paste_layout.addWidget(lbl_paste_title)

        self.paste_box = QPlainTextEdit(paste_card)
        self.paste_box.setPlaceholderText("Zehnaseeb\nManwa Laage\nArtist - Title also works")
        self.paste_box.setStyleSheet(f"background: transparent; border: none; color: {COLOR_TEXT_DARK}; font-family: monospace; font-size: 13px; line-height: 1.4;")
        self.paste_box.setMinimumHeight(85)
        paste_layout.addWidget(self.paste_box)

        cards_layout.addWidget(paste_card, 1)

        # Right Card: Save To
        save_card = QFrame(self)
        save_card.setObjectName("whiteCard")
        save_card.setStyleSheet(f"background-color: {COLOR_CARD_BG}; border: 1px solid {COLOR_CARD_BORDER}; border-radius: 16px; padding: 14px;")
        save_layout = QVBoxLayout(save_card)
        save_layout.setSpacing(8)

        lbl_save_title = QLabel("SAVE TO", save_card)
        lbl_save_title.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLOR_TEXT_UPPERCASE}; letter-spacing: 0.5px; border: none; background: transparent;")
        save_layout.addWidget(lbl_save_title)

        self.lbl_path = QLabel(self.output_dir, save_card)
        self.lbl_path.setStyleSheet(f"font-family: monospace; font-size: 13px; font-weight: 600; color: {COLOR_TEXT_DARK}; border: none; background: transparent;")
        self.lbl_path.setWordWrap(True)
        save_layout.addWidget(self.lbl_path)

        save_layout.addStretch()

        btn_change_dir = QPushButton("Change folder", save_card)
        btn_change_dir.setStyleSheet(SECONDARY_BUTTON_STYLE)
        btn_change_dir.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_change_dir.clicked.connect(self._change_output_dir)
        save_layout.addWidget(btn_change_dir, alignment=Qt.AlignmentFlag.AlignLeft)

        cards_layout.addWidget(save_card, 1)

        layout.addLayout(cards_layout)

        # Bottom Bar: CTA on Right
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        self.btn_review = QPushButton("Review list →", self)
        self.btn_review.setObjectName("primaryLimeBtn")
        self.btn_review.setStyleSheet(LIME_PILL_BUTTON_STYLE)
        self.btn_review.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_review.clicked.connect(self._on_review_clicked)
        bottom_bar.addWidget(self.btn_review)

        layout.addLayout(bottom_bar)

    def _handle_file_dropped(self, path: Path) -> None:
        self.selected_file_path = path
        self.drop_zone.set_selected_filename(path.name)

    def _browse_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Playlist File",
            "",
            "Supported Files (*.pdf *.docx *.csv *.txt);;PDF (*.pdf);;Word Documents (*.docx);;Text/CSV (*.txt *.csv);;All Files (*.*)",
        )
        if file_path:
            self._handle_file_dropped(Path(file_path))

    def _change_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.output_dir)
        if folder:
            self.output_dir = folder
            self.lbl_path.setText(folder)

    def _on_review_clicked(self) -> None:
        pasted = self.paste_box.toPlainText()
        self.on_parse_requested(self.selected_file_path, pasted, self.output_dir)

    def _on_start_clicked(self) -> None:
        """Alias for compatibility with tests."""
        self._on_review_clicked()
