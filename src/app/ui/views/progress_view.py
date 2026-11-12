"""Live batch progress screen with per-song states and aggregate metrics."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.models import DownloadJob


def make_stat_pill(label: str, count: int, color_hex: str) -> tuple[QWidget, QLabel]:
    """Helper to build a small colored metric pill."""
    pill = QFrame()
    pill.setStyleSheet(
        f"background-color: #1a1e27; border: 1px solid {color_hex}; border-radius: 6px; padding: 4px 10px;"
    )
    p_layout = QHBoxLayout(pill)
    p_layout.setContentsMargins(6, 2, 6, 2)
    p_layout.setSpacing(6)

    lbl_name = QLabel(label, pill)
    lbl_name.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 500; border: none; background: transparent;")

    lbl_count = QLabel(str(count), pill)
    lbl_count.setStyleSheet(f"color: {color_hex}; font-size: 13px; font-weight: bold; border: none; background: transparent;")

    p_layout.addWidget(lbl_name)
    p_layout.addWidget(lbl_count)
    return pill, lbl_count


class ProgressView(QWidget):
    """Real-time progress dashboard updating at 5 Hz without UI stutter."""

    def __init__(
        self,
        on_pause_toggled: Callable[[bool], None],
        on_cancel: Callable[[], None],
    ) -> None:
        super().__init__()
        self.on_pause_toggled = on_pause_toggled
        self.on_cancel = on_cancel
        self.is_paused = False
        self._job_row_map: dict[str, int] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header Title
        title = QLabel("Downloading Batch", self)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        # Aggregate Metrics Card
        metrics_card = QFrame(self)
        metrics_card.setStyleSheet("background-color: #16181f; border: 1px solid #23272e; border-radius: 8px; padding: 12px;")
        m_layout = QVBoxLayout(metrics_card)
        m_layout.setSpacing(10)

        # Overall progress bar
        pbar_layout = QHBoxLayout()
        self.overall_pbar = QProgressBar(metrics_card)
        self.overall_pbar.setRange(0, 100)
        self.overall_pbar.setValue(0)
        self.overall_pbar.setMinimumHeight(18)
        self.overall_pbar.setObjectName("successChunk")

        self.lbl_percentage = QLabel("0%", metrics_card)
        self.lbl_percentage.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff; min-width: 45px;")
        pbar_layout.addWidget(self.overall_pbar, 1)
        pbar_layout.addWidget(self.lbl_percentage)
        m_layout.addLayout(pbar_layout)

        # Speed and Stat Pills row
        pills_layout = QHBoxLayout()
        self.lbl_speed = QLabel("Speed: 0.0 MB/s", metrics_card)
        self.lbl_speed.setStyleSheet("color: #60a5fa; font-weight: 600; font-size: 13px;")
        pills_layout.addWidget(self.lbl_speed)

        self.lbl_eta = QLabel("ETA: --:--", metrics_card)
        self.lbl_eta.setStyleSheet("color: #94a3b8; font-size: 13px;")
        pills_layout.addWidget(self.lbl_eta)
        pills_layout.addStretch()

        pill_down, self.count_down_lbl = make_stat_pill("Downloaded", 0, "#10b981")
        pill_skip, self.count_skip_lbl = make_stat_pill("Skipped", 0, "#94a3b8")
        pill_not_found, self.count_not_found_lbl = make_stat_pill("Not Found", 0, "#f59e0b")
        pill_failed, self.count_failed_lbl = make_stat_pill("Failed", 0, "#ef4444")

        pills_layout.addWidget(pill_down)
        pills_layout.addWidget(pill_skip)
        pills_layout.addWidget(pill_not_found)
        pills_layout.addWidget(pill_failed)
        m_layout.addLayout(pills_layout)

        layout.addWidget(metrics_card)

        # Per-Song Progress Table
        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Artist", "Title", "Status", "Progress", "Speed / Info"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 140)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

        # Bottom Control Toolbar
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()

        self.btn_pause = QPushButton("Pause", self)
        self.btn_pause.setObjectName("secondaryButton")
        self.btn_pause.clicked.connect(self._toggle_pause)
        btn_bar.addWidget(self.btn_pause)

        self.btn_cancel = QPushButton("Cancel Batch", self)
        self.btn_cancel.setObjectName("dangerButton")
        self.btn_cancel.clicked.connect(self.on_cancel)
        btn_bar.addWidget(self.btn_cancel)

        layout.addLayout(btn_bar)

    def initialize_batch(self, jobs: list[DownloadJob]) -> None:
        """Initialize table rows for all jobs in the batch."""
        self._job_row_map.clear()
        self.table.setRowCount(len(jobs))
        self.overall_pbar.setValue(0)
        self.lbl_percentage.setText("0%")
        self.count_down_lbl.setText("0")
        self.count_skip_lbl.setText("0")
        self.count_not_found_lbl.setText("0")
        self.count_failed_lbl.setText("0")
        self.is_paused = False
        self.btn_pause.setText("Pause")

        for row, job in enumerate(jobs):
            self._job_row_map[job.id] = row

            item_art = QTableWidgetItem(job.song.artist or "Unknown")
            item_tit = QTableWidgetItem(job.song.title)
            item_st = QTableWidgetItem("queued")
            item_info = QTableWidgetItem("")

            pbar = QProgressBar()
            pbar.setRange(0, 100)
            pbar.setValue(0)

            self.table.setItem(row, 0, item_art)
            self.table.setItem(row, 1, item_tit)
            self.table.setItem(row, 2, item_st)
            self.table.setCellWidget(row, 3, pbar)
            self.table.setItem(row, 4, item_info)

    def update_job_status(self, job_id: str, status: str, error: str, output_path: str) -> None:
        """Update job lifecycle status badge and error/path details."""
        row = self._job_row_map.get(job_id)
        if row is None:
            return

        st_item = self.table.item(row, 2)
        if st_item:
            st_item.setText(status)
            if status == "done":
                st_item.setForeground(Qt.GlobalColor.green)
            elif status == "failed":
                st_item.setForeground(Qt.GlobalColor.red)
            elif status == "not_found":
                st_item.setForeground(Qt.GlobalColor.darkYellow)
            elif status == "skipped":
                st_item.setForeground(Qt.GlobalColor.gray)
            elif status == "downloading":
                st_item.setForeground(Qt.GlobalColor.cyan)

        # Update progress bar if complete
        pbar = self.table.cellWidget(row, 3)
        if isinstance(pbar, QProgressBar):
            if status in ("done", "skipped"):
                pbar.setValue(100)
            elif status in ("failed", "not_found"):
                pbar.setValue(0)

        info_item = self.table.item(row, 4)
        if info_item:
            if error:
                info_item.setText(error)
                info_item.setForeground(Qt.GlobalColor.red)
            elif output_path:
                info_item.setText("Saved")
                info_item.setForeground(Qt.GlobalColor.green)

    def update_job_progress(self, job_id: str, bytes_down: int, total_bytes: int, speed_bps: float) -> None:
        """Update per-song progress bar and instantaneous speed."""
        row = self._job_row_map.get(job_id)
        if row is None:
            return

        pbar = self.table.cellWidget(row, 3)
        if isinstance(pbar, QProgressBar) and total_bytes > 0:
            fraction = min(100, int((bytes_down / total_bytes) * 100))
            pbar.setValue(fraction)

        info_item = self.table.item(row, 4)
        if info_item and speed_bps > 0:
            speed_kb = speed_bps / 1024
            info_item.setText(f"{speed_kb:.0f} KB/s")

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
        """Update aggregate progress bar, speed, and metric pills."""
        if total > 0:
            pct = min(100, int((completed / total) * 100))
            self.overall_pbar.setValue(pct)
            self.lbl_percentage.setText(f"{pct}%")

        self.count_down_lbl.setText(str(downloaded))
        self.count_skip_lbl.setText(str(skipped))
        self.count_not_found_lbl.setText(str(not_found))
        self.count_failed_lbl.setText(str(failed))

        speed_mb = total_speed_bps / (1024 * 1024)
        self.lbl_speed.setText(f"Speed: {speed_mb:.2f} MB/s")

        # ETA calculation
        remaining_jobs = total - completed
        if total_speed_bps > 1000 and remaining_jobs > 0:
            # Estimate roughly 4 MB per remaining song
            est_seconds = int((remaining_jobs * 4 * 1024 * 1024) / total_speed_bps)
            mins = est_seconds // 60
            secs = est_seconds % 60
            self.lbl_eta.setText(f"ETA: {mins:02d}:{secs:02d}")
        else:
            self.lbl_eta.setText("ETA: --:--")

    def _toggle_pause(self) -> None:
        self.is_paused = not self.is_paused
        self.btn_pause.setText("Resume" if self.is_paused else "Pause")
        self.on_pause_toggled(self.is_paused)
