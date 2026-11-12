"""Import screen supporting drag-and-drop file ingestion, text pasting, and folder selection."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DropZoneWidget(QWidget):
    """Visual drag-and-drop zone accepting PDF, DOCX, CSV, and TXT files."""

    def __init__(self, on_file_dropped: Callable[[Path], None]) -> None:
        super().__init__()
        self.on_file_dropped = on_file_dropped
        self.setAcceptDrops(True)
        self.setStyleSheet(
            "border: 2px dashed #3b82f6; border-radius: 10px; background-color: #1a1e27; padding: 24px;"
        )

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel("📂", self)
        icon_lbl.setStyleSheet("font-size: 32px; border: none; background: transparent;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_lbl = QLabel("Drag & Drop your PDF, DOCX, CSV, or TXT playlist here\nor click Browse File below", self)
        text_lbl.setStyleSheet("color: #cbd5e1; font-size: 14px; font-weight: 500; border: none; background: transparent;")
        text_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon_lbl)
        layout.addWidget(text_lbl)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if urls:
            path = Path(urls[0].toLocalFile())
            self.on_file_dropped(path)


class ImportView(QWidget):
    """Primary import screen for loading playlists."""

    def __init__(
        self,
        default_output_dir: str,
        on_parse_requested: Callable[[Path | None, str, str], None],
    ) -> None:
        super().__init__()
        self.on_parse_requested = on_parse_requested
        self.selected_file_path: Path | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Title Header
        header = QLabel("Import Music Playlist", self)
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        layout.addWidget(header)

        # Drop Zone
        self.drop_zone = DropZoneWidget(self._handle_file_dropped)
        layout.addWidget(self.drop_zone)

        # Browse file button
        browse_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected", self)
        self.file_label.setStyleSheet("color: #94a3b8;")
        btn_browse_file = QPushButton("Browse File...", self)
        btn_browse_file.setObjectName("secondaryButton")
        btn_browse_file.clicked.connect(self._browse_file)
        browse_layout.addWidget(self.file_label, 1)
        browse_layout.addWidget(btn_browse_file)
        layout.addLayout(browse_layout)

        # Paste Text Area
        paste_group = QGroupBox("Or Paste Song Names Directly", self)
        p_layout = QVBoxLayout(paste_group)
        self.paste_box = QPlainTextEdit(paste_group)
        self.paste_box.setPlaceholderText(
            "Paste songs here (one per line). Examples:\n"
            "Queen - Bohemian Rhapsody\n"
            "Imagine by John Lennon\n"
            "Pink Floyd - Comfortably Numb"
        )
        self.paste_box.setMaximumHeight(130)
        p_layout.addWidget(self.paste_box)
        layout.addWidget(paste_group)

        # Output Folder Picker
        folder_group = QGroupBox("Destination Folder", self)
        f_layout = QHBoxLayout(folder_group)
        self.output_dir_input = QLineEdit(default_output_dir, folder_group)
        btn_browse_dir = QPushButton("Browse...", folder_group)
        btn_browse_dir.setObjectName("secondaryButton")
        btn_browse_dir.clicked.connect(self._browse_output_dir)
        f_layout.addWidget(self.output_dir_input, 1)
        f_layout.addWidget(btn_browse_dir)
        layout.addWidget(folder_group)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_parse = QPushButton("Parse & Review Playlist →", self)
        self.btn_parse.setMinimumHeight(38)
        self.btn_parse.clicked.connect(self._on_start_clicked)
        btn_layout.addWidget(self.btn_parse)
        layout.addLayout(btn_layout)

    def _browse_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Playlist File",
            "",
            "Playlist Files (*.pdf *.docx *.csv *.txt);;PDF (*.pdf);;DOCX (*.docx);;CSV (*.csv);;TXT (*.txt);;All Files (*.*)",
        )
        if file_path:
            self._handle_file_dropped(Path(file_path))

    def _handle_file_dropped(self, path: Path) -> None:
        self.selected_file_path = path
        self.file_label.setText(f"Selected: {path.name} ({path.stat().st_size // 1024} KB)")
        self.file_label.setStyleSheet("color: #60a5fa; font-weight: 500;")

    def _browse_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder", self.output_dir_input.text())
        if folder:
            self.output_dir_input.setText(folder)

    def _on_start_clicked(self) -> None:
        pasted = self.paste_box.toPlainText().strip()
        out_dir = self.output_dir_input.text().strip()
        self.on_parse_requested(self.selected_file_path, pasted, out_dir)

