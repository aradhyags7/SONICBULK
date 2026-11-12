"""Live batch progress screen with audio visualizer hero and split activity cards."""

from __future__ import annotations

import math
import time
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.models import DownloadJob
from app.ui.theme import (
    COLOR_CARD_BG,
    COLOR_CARD_BORDER,
    COLOR_DARK_HERO,
    COLOR_LIME,
    COLOR_TEXT_DARK,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_UPPERCASE,
    SECONDARY_BUTTON_STYLE,
)


class AudioVisualizerWidget(QWidget):
    """Custom painted audio soundwave bar visualizer reflecting batch progress."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(38)
        self.progress_fraction = 0.0  # 0.0 to 1.0

        # Pre-calculated pleasant waveform heights (58 bars)
        self._height_factors = [
            0.3, 0.4, 0.7, 0.9, 0.6, 0.4, 0.5, 0.8, 1.0, 0.7,
            0.5, 0.3, 0.6, 0.85, 0.75, 0.4, 0.65, 0.9, 0.5, 0.35,
            0.45, 0.8, 0.95, 0.6, 0.4, 0.55, 0.75, 0.85, 0.65, 0.4,
            0.5, 0.7, 0.9, 1.0, 0.8, 0.45, 0.6, 0.75, 0.85, 0.5,
            0.35, 0.65, 0.8, 0.95, 0.7, 0.4, 0.5, 0.85, 0.6, 0.45,
            0.35, 0.55, 0.75, 0.9, 0.65, 0.4, 0.5, 0.35,
        ]

    def set_progress(self, fraction: float) -> None:
        self.progress_fraction = max(0.0, min(1.0, fraction))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        bar_count = len(self._height_factors)
        bar_width = max(2.5, (width - (bar_count - 1) * 4) / bar_count)
        spacing = 4.0

        filled_count = int(self.progress_fraction * bar_count)

        color_active = QColor(COLOR_LIME)  # Vibrant lime
        color_inactive = QColor("#223326")  # Dark pine muted

        for i, factor in enumerate(self._height_factors):
            x = i * (bar_width + spacing)
            bar_h = max(6.0, height * factor * 0.9)
            y = (height - bar_h) / 2.0

            color = color_active if i <= filled_count else color_inactive
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(x, y, bar_width, bar_h, 1.5, 1.5)


class InProgressRowWidget(QWidget):
    """Row item in the IN PROGRESS card with song title, status, and mini bar."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(34)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.lbl_title = QLabel(title, self)
        self.lbl_title.setStyleSheet(f"font-weight: 700; color: {COLOR_TEXT_DARK}; font-size: 13px; border: none; background: transparent; padding: 0px;")
        self.lbl_title.setMinimumWidth(160)
        layout.addWidget(self.lbl_title, 1)

        self.lbl_status = QLabel("Searching", self)
        self.lbl_status.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px; border: none; background: transparent; padding: 0px;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_status.setMinimumWidth(110)
        layout.addWidget(self.lbl_status)

        self.pbar = QProgressBar(self)
        self.pbar.setRange(0, 100)
        self.pbar.setValue(5)
        self.pbar.setTextVisible(False)
        self.pbar.setFixedHeight(5)
        self.pbar.setFixedWidth(65)
        self.pbar.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: #e5ebe2;
                border-radius: 2px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {COLOR_TEXT_DARK};
                border-radius: 2px;
            }}
            """
        )
        layout.addWidget(self.pbar)

    def update_state(self, status: str, pct: int = 0) -> None:
        if status == "downloading":
            self.lbl_status.setText(f"Downloading {pct}%")
            self.pbar.setValue(max(5, pct))
        elif status == "tagging":
            self.lbl_status.setText("Tagging")
            self.pbar.setValue(90)
        elif status in ("matching", "resolving"):
            self.lbl_status.setText("Matching")
            self.pbar.setValue(25)
        elif status == "searching":
            self.lbl_status.setText("Searching")
            self.pbar.setValue(10)
        else:
            self.lbl_status.setText(status.capitalize())
            self.pbar.setValue(pct)


class JustFinishedRowWidget(QWidget):
    """Row item in the JUST FINISHED card with title and green checkmark."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(34)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        lbl_title = QLabel(title, self)
        lbl_title.setStyleSheet(f"font-weight: 500; color: {COLOR_TEXT_DARK}; font-size: 13px; border: none; background: transparent; padding: 0px;")
        layout.addWidget(lbl_title, 1)

        lbl_check = QLabel("✓", self)
        lbl_check.setStyleSheet("color: #1b7340; font-weight: 800; font-size: 15px; border: none; background: transparent; padding: 0px;")
        layout.addWidget(lbl_check)


class ProgressView(QWidget):
    """Live progress dashboard matching the design specification."""

    def __init__(
        self,
        on_pause_toggled: Callable[[bool], None],
        on_cancel: Callable[[], None],
    ) -> None:
        super().__init__()
        self.on_pause_toggled = on_pause_toggled
        self.on_cancel = on_cancel
        self.is_paused = False

        self._start_time: float = 0.0
        self._jobs: dict[str, DownloadJob] = {}
        self._job_row_map: dict[str, int] = {}
        self._in_progress_widgets: dict[str, InProgressRowWidget] = {}
        self._finished_job_ids: set[str] = set()

        # Compatibility members for tests & aggregate reporting
        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setVisible(False)
        self.overall_pbar = QProgressBar(self)
        self.overall_pbar.setVisible(False)
        self.lbl_speed = QLabel("Speed: 0.0 MB/s", self)
        self.lbl_speed.setVisible(False)
        self.count_down_lbl = QLabel("0", self)
        self.count_down_lbl.setVisible(False)
        self.count_skip_lbl = QLabel("0", self)
        self.count_skip_lbl.setVisible(False)
        self.count_not_found_lbl = QLabel("0", self)
        self.count_not_found_lbl.setVisible(False)
        self.count_failed_lbl = QLabel("0", self)
        self.count_failed_lbl.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 36, 40, 36)
        layout.setSpacing(20)

        # Top Bar: Title & Pause / Cancel buttons
        top_bar = QHBoxLayout()
        title = QLabel("Downloading", self)
        title.setStyleSheet(f"font-size: 32px; font-weight: 800; color: {COLOR_TEXT_DARK}; letter-spacing: -0.5px;")
        top_bar.addWidget(title)

        top_bar.addStretch()

        self.btn_pause = QPushButton("Pause", self)
        self.btn_pause.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pause.clicked.connect(self._toggle_pause)
        top_bar.addWidget(self.btn_pause)

        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.on_cancel)
        top_bar.addWidget(self.btn_cancel)

        layout.addLayout(top_bar)

        # Hero Dark Card with Big Count, Stats & Visualizer Wave
        hero_card = QFrame(self)
        hero_card.setObjectName("darkHeroCard")
        hero_card.setStyleSheet(
            f"background-color: {COLOR_DARK_HERO}; border-radius: 20px; border: none;"
        )
        hero_layout = QVBoxLayout(hero_card)
        hero_layout.setContentsMargins(24, 24, 24, 24)
        hero_layout.setSpacing(20)

        stats_row = QHBoxLayout()
        stats_row.setContentsMargins(0, 0, 0, 0)

        # Big Count on Left
        count_box = QHBoxLayout()
        count_box.setSpacing(8)
        count_box.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.lbl_downloaded_count = QLabel("0", hero_card)
        self.lbl_downloaded_count.setStyleSheet(
            f"color: {COLOR_LIME}; font-size: 58px; font-weight: 800; line-height: 1; border: none; background: transparent; padding: 0px;"
        )
        count_box.addWidget(self.lbl_downloaded_count)

        self.lbl_total_count = QLabel("of 0 songs", hero_card)
        self.lbl_total_count.setStyleSheet(
            "color: #ffffff; font-size: 16px; font-weight: 500; border: none; background: transparent; padding: 0px; padding-top: 18px;"
        )
        count_box.addWidget(self.lbl_total_count)
        stats_row.addLayout(count_box)

        stats_row.addStretch()

        # Metrics on Right: SPEED, TIME LEFT, ELAPSED
        metrics_box = QHBoxLayout()
        metrics_box.setSpacing(28)

        # Speed
        col_speed = QVBoxLayout()
        col_speed.setSpacing(2)
        lbl_s_hdr = QLabel("SPEED", hero_card)
        lbl_s_hdr.setStyleSheet("color: #7d9182; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; border: none; background: transparent; padding: 0px;")
        self.lbl_speed_val = QLabel("0.0 MB/s", hero_card)
        self.lbl_speed_val.setStyleSheet("color: #ffffff; font-size: 17px; font-weight: 700; border: none; background: transparent; padding: 0px;")
        col_speed.addWidget(lbl_s_hdr)
        col_speed.addWidget(self.lbl_speed_val)
        metrics_box.addLayout(col_speed)

        # Time Left
        col_left = QVBoxLayout()
        col_left.setSpacing(2)
        lbl_l_hdr = QLabel("TIME LEFT", hero_card)
        lbl_l_hdr.setStyleSheet("color: #7d9182; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; border: none; background: transparent; padding: 0px;")
        self.lbl_eta_val = QLabel("--:--", hero_card)
        self.lbl_eta_val.setStyleSheet("color: #ffffff; font-size: 17px; font-weight: 700; border: none; background: transparent; padding: 0px;")
        col_left.addWidget(lbl_l_hdr)
        col_left.addWidget(self.lbl_eta_val)
        metrics_box.addLayout(col_left)

        # Elapsed
        col_el = QVBoxLayout()
        col_el.setSpacing(2)
        lbl_e_hdr = QLabel("ELAPSED", hero_card)
        lbl_e_hdr.setStyleSheet("color: #7d9182; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; border: none; background: transparent; padding: 0px;")
        self.lbl_elapsed_val = QLabel("0s", hero_card)
        self.lbl_elapsed_val.setStyleSheet("color: #ffffff; font-size: 17px; font-weight: 700; border: none; background: transparent; padding: 0px;")
        col_el.addWidget(lbl_e_hdr)
        col_el.addWidget(self.lbl_elapsed_val)
        metrics_box.addLayout(col_el)

        stats_row.addLayout(metrics_box)
        hero_layout.addLayout(stats_row)

        # Audio Wave Visualizer
        self.visualizer = AudioVisualizerWidget(hero_card)
        hero_layout.addWidget(self.visualizer)

        layout.addWidget(hero_card)

        # Bottom Two Cards: IN PROGRESS and JUST FINISHED
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        # Left Card: IN PROGRESS
        self.in_progress_card = QFrame(self)
        self.in_progress_card.setObjectName("whiteCard")
        self.in_progress_card.setStyleSheet(f"background-color: {COLOR_CARD_BG}; border: 1px solid {COLOR_CARD_BORDER}; border-radius: 16px;")
        self.in_progress_layout = QVBoxLayout(self.in_progress_card)
        self.in_progress_layout.setContentsMargins(20, 18, 20, 18)
        self.in_progress_layout.setSpacing(8)

        lbl_inp_hdr = QLabel("IN PROGRESS", self.in_progress_card)
        lbl_inp_hdr.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLOR_TEXT_UPPERCASE}; letter-spacing: 0.5px; border: none; background: transparent; padding: 0px;")
        self.in_progress_layout.addWidget(lbl_inp_hdr)

        self.in_progress_container = QVBoxLayout()
        self.in_progress_container.setSpacing(4)
        self.in_progress_layout.addLayout(self.in_progress_container)
        self.in_progress_layout.addStretch()

        cards_layout.addWidget(self.in_progress_card, 1)

        # Right Card: JUST FINISHED
        self.finished_card = QFrame(self)
        self.finished_card.setObjectName("whiteCard")
        self.finished_card.setStyleSheet(f"background-color: {COLOR_CARD_BG}; border: 1px solid {COLOR_CARD_BORDER}; border-radius: 16px;")
        self.finished_layout = QVBoxLayout(self.finished_card)
        self.finished_layout.setContentsMargins(20, 18, 20, 18)
        self.finished_layout.setSpacing(8)

        lbl_fin_hdr = QLabel("JUST FINISHED", self.finished_card)
        lbl_fin_hdr.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLOR_TEXT_UPPERCASE}; letter-spacing: 0.5px; border: none; background: transparent; padding: 0px;")
        self.finished_layout.addWidget(lbl_fin_hdr)

        self.finished_container = QVBoxLayout()
        self.finished_container.setSpacing(4)
        self.finished_layout.addLayout(self.finished_container)
        self.finished_layout.addStretch()

        cards_layout.addWidget(self.finished_card, 1)

        layout.addLayout(cards_layout, 1)

    def initialize_batch(self, jobs: list[DownloadJob]) -> None:
        """Reset and prepare for new batch run."""
        self._start_time = time.monotonic()
        self._jobs = {j.id: j for j in jobs}
        self._finished_job_ids.clear()
        self.is_paused = False
        self.btn_pause.setText("Pause")

        # Compatibility table
        self._job_row_map.clear()
        self.table.setRowCount(len(jobs))
        for row, job in enumerate(jobs):
            self._job_row_map[job.id] = row
            self.table.setItem(row, 0, QTableWidgetItem(job.song.artist or "Unknown"))
            self.table.setItem(row, 1, QTableWidgetItem(job.song.title))
            self.table.setItem(row, 2, QTableWidgetItem("queued"))
            pbar = QProgressBar()
            pbar.setRange(0, 100)
            pbar.setValue(0)
            self.table.setCellWidget(row, 3, pbar)
            self.table.setItem(row, 4, QTableWidgetItem(""))

        # Clear containers
        for w in self._in_progress_widgets.values():
            w.deleteLater()
        self._in_progress_widgets.clear()

        # Clear finished items
        while self.finished_container.count() > 0:
            item = self.finished_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.lbl_downloaded_count.setText("0")
        self.lbl_total_count.setText(f"of {len(jobs)} songs")
        self.lbl_speed_val.setText("0.0 MB/s")
        self.lbl_eta_val.setText("--:--")
        self.lbl_elapsed_val.setText("0s")
        self.visualizer.set_progress(0.0)

    def update_job_status(self, job_id: str, status: str, error: str, output_path: str) -> None:
        """Handle individual song lifecycle status changes."""
        row = self._job_row_map.get(job_id)
        if row is not None:
            st_item = self.table.item(row, 2)
            if st_item:
                st_item.setText(status)
            pbar = self.table.cellWidget(row, 3)
            if isinstance(pbar, QProgressBar):
                if status in ("done", "skipped"):
                    pbar.setValue(100)
                elif status in ("failed", "not_found"):
                    pbar.setValue(0)

        job = self._jobs.get(job_id)
        if not job:
            return

        # If job is active, show in IN PROGRESS list
        if status in ("searching", "matched", "resolving", "downloading", "tagging"):
            if job_id not in self._in_progress_widgets:
                if len(self._in_progress_widgets) >= 5:
                    first_k = next(iter(self._in_progress_widgets))
                    w_old = self._in_progress_widgets.pop(first_k)
                    w_old.deleteLater()
                row_w = InProgressRowWidget(job.song.title, self.in_progress_card)
                self._in_progress_widgets[job_id] = row_w
                self.in_progress_container.addWidget(row_w)
            self._in_progress_widgets[job_id].update_state(status)

        # If job completed, remove from in progress and add to JUST FINISHED
        elif status in ("done", "skipped"):
            if job_id in self._in_progress_widgets:
                w = self._in_progress_widgets.pop(job_id)
                w.deleteLater()

            if job_id not in self._finished_job_ids:
                self._finished_job_ids.add(job_id)
                if self.finished_container.count() >= 5:
                    first_item = self.finished_container.takeAt(0)
                    if first_item.widget():
                        first_item.widget().deleteLater()
                fin_row = JustFinishedRowWidget(job.song.title, self.finished_card)
                self.finished_container.addWidget(fin_row)

        elif status in ("failed", "not_found"):
            if job_id in self._in_progress_widgets:
                w = self._in_progress_widgets.pop(job_id)
                w.deleteLater()

    def update_job_progress(self, job_id: str, bytes_down: int, total_bytes: int, speed_bps: float) -> None:
        """Update active song progress in the left card."""
        row = self._job_row_map.get(job_id)
        if row is not None and total_bytes and total_bytes > 0:
            pbar = self.table.cellWidget(row, 3)
            if isinstance(pbar, QProgressBar):
                pbar.setValue(min(100, int((bytes_down / total_bytes) * 100)))

        w = self._in_progress_widgets.get(job_id)
        if w and total_bytes and total_bytes > 0:
            pct = min(100, int((bytes_down / total_bytes) * 100))
            w.update_state("downloading", pct)

    def update_batch_progress(
        self,
        total: int,
        completed: int,
        downloaded: int,
        skipped: int,
        not_found: int,
        failed: int,
        active: int,
        total_speed_bps: float,
    ) -> None:
        """Update hero card metrics and visualizer wave."""
        self.count_down_lbl.setText(str(downloaded))
        self.count_skip_lbl.setText(str(skipped))
        self.count_not_found_lbl.setText(str(not_found))
        self.count_failed_lbl.setText(str(failed))
        if total > 0:
            self.overall_pbar.setValue(min(100, int((completed / total) * 100)))

        self.lbl_downloaded_count.setText(str(downloaded))
        self.lbl_total_count.setText(f"of {total} songs")

        fraction = (downloaded + skipped) / max(1, total)
        self.visualizer.set_progress(fraction)

        # Speed
        speed_mb = total_speed_bps / (1024 * 1024)
        self.lbl_speed_val.setText(f"{speed_mb:.1f} MB/s")

        # Elapsed
        if self._start_time > 0:
            elapsed = int(time.monotonic() - self._start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            self.lbl_elapsed_val.setText(f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s")

            # ETA
            remaining = total - (downloaded + skipped + not_found + failed)
            if remaining > 0 and downloaded > 0:
                avg_time_per_song = elapsed / max(1, downloaded)
                rem_secs = int(remaining * avg_time_per_song)
                r_mins = rem_secs // 60
                r_s = rem_secs % 60
                self.lbl_eta_val.setText(f"{r_mins}m {r_s:02d}s" if r_mins > 0 else f"{r_s}s")
            elif remaining == 0:
                self.lbl_eta_val.setText("0s")

    def _toggle_pause(self) -> None:
        self.is_paused = not self.is_paused
        self.btn_pause.setText("Resume" if self.is_paused else "Pause")
        self.on_pause_toggled(self.is_paused)
