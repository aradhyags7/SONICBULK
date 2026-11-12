"""Settings configuration screen matching the clean editorial design."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.config import AppSettings


class SettingsView(QWidget):
    """Full application settings editor with white card styling."""

    def __init__(
        self,
        settings: AppSettings,
        on_save_settings: Callable[[AppSettings], None],
        on_back: Callable[[], None],
    ) -> None:
        super().__init__()
        self.settings = settings
        self.on_save_settings = on_save_settings
        self.on_back = on_back

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 36, 40, 36)
        main_layout.setSpacing(20)

        # Header Title
        top_bar = QHBoxLayout()
        title = QLabel("Settings & Preferences", self)
        title.setStyleSheet("font-size: 32px; font-weight: 800; color: #111813; letter-spacing: -0.5px;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        btn_back = QPushButton("← Back", self)
        btn_back.clicked.connect(self.on_back)
        top_bar.addWidget(btn_back)
        main_layout.addLayout(top_bar)

        # Scrollable container for settings cards
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(16)
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        # 1. Output & Organization Card
        card_output = QFrame(scroll_content)
        card_output.setObjectName("whiteCard")
        card_output.setStyleSheet("background-color: #ffffff; border: 1px solid #d8ddcf; border-radius: 16px; padding: 20px;")
        form_output = QFormLayout(card_output)
        form_output.setSpacing(12)

        lbl_hdr1 = QLabel("OUTPUT & FOLDER ORGANIZATION", card_output)
        lbl_hdr1.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px; border: none; background: transparent;")
        form_output.addRow(lbl_hdr1)

        out_layout = QHBoxLayout()
        self.input_output_dir = QLineEdit(settings.output_dir, card_output)
        btn_browse = QPushButton("Browse...", card_output)
        btn_browse.clicked.connect(self._browse_dir)
        out_layout.addWidget(self.input_output_dir, 1)
        out_layout.addWidget(btn_browse)
        form_output.addRow("Output Folder:", out_layout)

        self.combo_layout = QComboBox(card_output)
        self.combo_layout.addItems(["flat", "artist_album"])
        self.combo_layout.setCurrentText(settings.folder_layout)
        form_output.addRow("Folder Structure:", self.combo_layout)

        self.input_template = QLineEdit(settings.filename_template, card_output)
        form_output.addRow("Filename Template:", self.input_template)

        self.combo_format = QComboBox(card_output)
        self.combo_format.addItems(["native", "mp3", "m4a", "flac"])
        self.combo_format.setCurrentText(settings.output_format)
        form_output.addRow("Output Format:", self.combo_format)

        scroll_layout.addWidget(card_output)

        # 2. Concurrency & Performance Card
        card_perf = QFrame(scroll_content)
        card_perf.setObjectName("whiteCard")
        card_perf.setStyleSheet("background-color: #ffffff; border: 1px solid #d8ddcf; border-radius: 16px; padding: 20px;")
        form_perf = QFormLayout(card_perf)
        form_perf.setSpacing(12)

        lbl_hdr2 = QLabel("PIPELINE CONCURRENCY (STAGES)", card_perf)
        lbl_hdr2.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px; border: none; background: transparent;")
        form_perf.addRow(lbl_hdr2)

        self.spin_download = QSpinBox(card_perf)
        self.spin_download.setRange(1, 16)
        self.spin_download.setValue(settings.download_concurrency)
        self.spin_download.setToolTip("Default: 1 sequential for polite, reliable downloads. Scalable up to 16.")
        form_perf.addRow("Download Concurrency:", self.spin_download)

        self.spin_search = QSpinBox(card_perf)
        self.spin_search.setRange(1, 16)
        self.spin_search.setValue(settings.search_concurrency)
        form_perf.addRow("Search Concurrency:", self.spin_search)

        self.spin_resolve = QSpinBox(card_perf)
        self.spin_resolve.setRange(1, 16)
        self.spin_resolve.setValue(settings.resolve_concurrency)
        form_perf.addRow("Resolve Concurrency:", self.spin_resolve)

        scroll_layout.addWidget(card_perf)

        # 3. Provider & Matching Card
        card_match = QFrame(scroll_content)
        card_match.setObjectName("whiteCard")
        card_match.setStyleSheet("background-color: #ffffff; border: 1px solid #d8ddcf; border-radius: 16px; padding: 20px;")
        form_match = QFormLayout(card_match)
        form_match.setSpacing(12)

        lbl_hdr3 = QLabel("MATCH THRESHOLDS & CACHE", card_match)
        lbl_hdr3.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px; border: none; background: transparent;")
        form_match.addRow(lbl_hdr3)

        self.spin_th_high = QDoubleSpinBox(card_match)
        self.spin_th_high.setRange(0.50, 1.00)
        self.spin_th_high.setSingleStep(0.05)
        self.spin_th_high.setValue(settings.threshold_high)
        form_match.addRow("Auto-Accept Threshold (High):", self.spin_th_high)

        self.spin_th_low = QDoubleSpinBox(card_match)
        self.spin_th_low.setRange(0.20, 0.80)
        self.spin_th_low.setSingleStep(0.05)
        self.spin_th_low.setValue(settings.threshold_low)
        form_match.addRow("Minimum Score Threshold (Low):", self.spin_th_low)

        self.chk_prevent_sleep = QCheckBox("Inhibit OS sleep during active downloads", card_match)
        self.chk_prevent_sleep.setChecked(settings.prevent_sleep)
        form_match.addRow("", self.chk_prevent_sleep)

        scroll_layout.addWidget(card_match)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        self.btn_save = QPushButton("Save Settings", self)
        self.btn_save.setObjectName("primaryLimeBtn")
        self.btn_save.setMinimumHeight(44)
        self.btn_save.clicked.connect(self._on_save)
        bottom_bar.addWidget(self.btn_save)

        main_layout.addLayout(bottom_bar)

    def _browse_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.input_output_dir.text())
        if folder:
            self.input_output_dir.setText(folder)

    def _on_save(self) -> None:
        new_settings = AppSettings(
            output_dir=self.input_output_dir.text().strip(),
            folder_layout=self.combo_layout.currentText(),
            filename_template=self.input_template.text().strip(),
            output_format=self.combo_format.currentText(),
            search_concurrency=self.spin_search.value(),
            resolve_concurrency=self.spin_resolve.value(),
            download_concurrency=self.spin_download.value(),
            threshold_high=self.spin_th_high.value(),
            threshold_low=self.spin_th_low.value(),
            prevent_sleep=self.chk_prevent_sleep.isChecked(),
        )
        self.on_save_settings(new_settings)

    def _save(self) -> None:
        """Alias for compatibility with tests."""
        self._on_save()
