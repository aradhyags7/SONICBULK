"""Settings configuration screen with live bounds validation."""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.config import AppSettings


class SettingsView(QWidget):
    """Full application settings editor."""

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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Settings & Preferences", self)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        # 1. Output & Organization Group
        grp_output = QGroupBox("Output & Folder Layout", self)
        form_output = QFormLayout(grp_output)

        out_layout = QHBoxLayout()
        self.input_output_dir = QLineEdit(settings.output_dir, grp_output)
        btn_browse = QPushButton("Browse...", grp_output)
        btn_browse.setObjectName("secondaryButton")
        btn_browse.clicked.connect(self._browse_dir)
        out_layout.addWidget(self.input_output_dir, 1)
        out_layout.addWidget(btn_browse)
        form_output.addRow("Output Folder:", out_layout)

        self.combo_layout = QComboBox(grp_output)
        self.combo_layout.addItems(["flat", "artist_album"])
        self.combo_layout.setCurrentText(settings.folder_layout)
        form_output.addRow("Folder Structure:", self.combo_layout)

        self.input_template = QLineEdit(settings.filename_template, grp_output)
        form_output.addRow("Filename Template:", self.input_template)

        self.combo_format = QComboBox(grp_output)
        self.combo_format.addItems(["native", "mp3", "m4a", "flac"])
        self.combo_format.setCurrentText(settings.output_format)
        form_output.addRow("Output Format:", self.combo_format)

        layout.addWidget(grp_output)

        # 2. Concurrency & Performance Group
        grp_perf = QGroupBox("Pipeline Concurrency (Stages)", self)
        form_perf = QFormLayout(grp_perf)

        self.spin_download = QSpinBox(grp_perf)
        self.spin_download.setRange(1, 16)
        self.spin_download.setValue(settings.download_concurrency)
        form_perf.addRow("Download Concurrency (1-16):", self.spin_download)

        self.spin_search = QSpinBox(grp_perf)
        self.spin_search.setRange(1, 32)
        self.spin_search.setValue(settings.search_concurrency)
        form_perf.addRow("Search Concurrency (1-32):", self.spin_search)

        self.spin_resolve = QSpinBox(grp_perf)
        self.spin_resolve.setRange(1, 32)
        self.spin_resolve.setValue(settings.resolve_concurrency)
        form_perf.addRow("Resolve Concurrency (1-32):", self.spin_resolve)

        layout.addWidget(grp_perf)

        # 3. Matching Thresholds Group
        grp_match = QGroupBox("Matching Confidence Thresholds", self)
        form_match = QFormLayout(grp_match)

        self.spin_high = QDoubleSpinBox(grp_match)
        self.spin_high.setRange(0.5, 1.0)
        self.spin_high.setSingleStep(0.05)
        self.spin_high.setValue(settings.threshold_high)
        form_match.addRow("Auto-Accept Threshold (High):", self.spin_high)

        self.spin_low = QDoubleSpinBox(grp_match)
        self.spin_low.setRange(0.1, 0.9)
        self.spin_low.setSingleStep(0.05)
        self.spin_low.setValue(settings.threshold_low)
        form_match.addRow("Minimum Match Threshold (Low):", self.spin_low)

        layout.addWidget(grp_match)

        # 4. Sources & Toggles
        grp_misc = QGroupBox("Sources & Advanced", self)
        form_misc = QFormLayout(grp_misc)

        self.chk_ytdlp = QCheckBox("Enable yt-dlp Provider (worker subprocess pool)", grp_misc)
        self.chk_ytdlp.setChecked(settings.ytdlp_enabled)
        form_misc.addRow(self.chk_ytdlp)

        self.chk_sleep = QCheckBox("Prevent System Sleep During Active Downloads", grp_misc)
        self.chk_sleep.setChecked(settings.prevent_sleep)
        form_misc.addRow(self.chk_sleep)

        layout.addWidget(grp_misc)

        # Bottom Buttons
        bottom_bar = QHBoxLayout()
        btn_back = QPushButton("← Back", self)
        btn_back.setObjectName("secondaryButton")
        btn_back.clicked.connect(self.on_back)
        bottom_bar.addWidget(btn_back)

        bottom_bar.addStretch()

        btn_save = QPushButton("Save Settings", self)
        btn_save.clicked.connect(self._save)
        bottom_bar.addWidget(btn_save)

        layout.addLayout(bottom_bar)

    def _browse_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.input_output_dir.text())
        if folder:
            self.input_output_dir.setText(folder)

    def _save(self) -> None:
        self.settings.output_dir = self.input_output_dir.text().strip()
        self.settings.folder_layout = self.combo_layout.currentText()
        self.settings.filename_template = self.input_template.text().strip()
        self.settings.output_format = self.combo_format.currentText()
        self.settings.download_concurrency = self.spin_download.value()
        self.settings.search_concurrency = self.spin_search.value()
        self.settings.resolve_concurrency = self.spin_resolve.value()
        self.settings.threshold_high = self.spin_high.value()
        self.settings.threshold_low = self.spin_low.value()
        self.settings.ytdlp_enabled = self.chk_ytdlp.isChecked()
        self.settings.prevent_sleep = self.chk_sleep.isChecked()
        self.settings.validate()
        self.on_save_settings(self.settings)
