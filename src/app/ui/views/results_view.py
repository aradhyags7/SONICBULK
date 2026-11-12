"""Results and final audit report screen with candidate swapping and retry capabilities."""

from __future__ import annotations

import csv
import os
import subprocess
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.models import BatchSummary, Candidate, Confidence, DownloadJob


class CandidateSwapDialog(QDialog):
    """Modal dialog allowing the user to select an alternative candidate for a low-confidence match."""

    def __init__(self, parent: QWidget, song_title: str, candidates: list[Candidate]) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Swap Candidate: {song_title}")
        self.resize(650, 350)
        self.selected_candidate: Candidate | None = None

        layout = QVBoxLayout(self)

        lbl = QLabel(f"Available Candidate Matches for '{song_title}':", self)
        lbl.setStyleSheet("font-weight: bold; color: #ffffff;")
        layout.addWidget(lbl)

        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Provider", "Title", "Artist", "Score", "Duration"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        self.table.setRowCount(len(candidates))
        for row, c in enumerate(candidates):
            self.table.setItem(row, 0, QTableWidgetItem(c.provider))
            self.table.setItem(row, 1, QTableWidgetItem(c.title))
            self.table.setItem(row, 2, QTableWidgetItem(c.artist or "Unknown"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{c.score:.2f}"))
            dur_str = f"{int(c.duration_seconds // 60)}:{int(c.duration_seconds % 60):02d}" if c.duration_seconds else "--:--"
            self.table.setItem(row, 4, QTableWidgetItem(dur_str))

        layout.addWidget(self.table)

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.setObjectName("secondaryButton")
        btn_cancel.clicked.connect(self.reject)

        btn_select = QPushButton("Use This Candidate", self)
        btn_select.clicked.connect(lambda: self._choose(candidates))

        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_select)
        layout.addLayout(btn_box)

    def _choose(self, candidates: list[Candidate]) -> None:
        selected_indexes = self.table.selectedIndexes()
        if selected_indexes:
            row = selected_indexes[0].row()
            if 0 <= row < len(candidates):
                self.selected_candidate = candidates[row]
                self.accept()


class ResultsView(QWidget):
    """Final summary report screen."""

    def __init__(
        self,
        output_dir: str,
        on_retry_failed: Callable[[list[DownloadJob]], None],
        on_new_import: Callable[[], None],
        fetch_candidates_func: Callable[[str], list[Candidate]] | None = None,
    ) -> None:
        super().__init__()
        self.output_dir = output_dir
        self.on_retry_failed = on_retry_failed
        self.on_new_import = on_new_import
        self.fetch_candidates_func = fetch_candidates_func
        self.jobs: list[DownloadJob] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Title
        title = QLabel("Batch Download Complete", self)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        # Summary Header Card
        self.summary_card = QFrame(self)
        self.summary_card.setStyleSheet("background-color: #16181f; border: 1px solid #23272e; border-radius: 8px; padding: 14px;")
        s_layout = QHBoxLayout(self.summary_card)

        self.lbl_stats = QLabel("Summary: 0 Downloaded | 0 Skipped | 0 Not Found | 0 Failed", self.summary_card)
        self.lbl_stats.setStyleSheet("font-size: 15px; font-weight: 600; color: #ffffff;")
        s_layout.addWidget(self.lbl_stats)
        s_layout.addStretch()

        btn_open_folder = QPushButton("📂 Open Output Folder", self.summary_card)
        btn_open_folder.setObjectName("secondaryButton")
        btn_open_folder.clicked.connect(self._open_output_folder)
        s_layout.addWidget(btn_open_folder)

        layout.addWidget(self.summary_card)

        # Results Table
        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Artist", "Title", "Status", "Confidence", "Match Result", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 120)
        layout.addWidget(self.table)

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()

        btn_new = QPushButton("New Import", self)
        btn_new.setObjectName("secondaryButton")
        btn_new.clicked.connect(self.on_new_import)
        bottom_bar.addWidget(btn_new)

        bottom_bar.addStretch()

        btn_export = QPushButton("Export Report CSV", self)
        btn_export.setObjectName("secondaryButton")
        btn_export.clicked.connect(self._export_csv)
        bottom_bar.addWidget(btn_export)

        self.btn_retry = QPushButton("Retry Failed (0) ↺", self)
        self.btn_retry.setObjectName("dangerButton")
        self.btn_retry.clicked.connect(self._retry_failed_clicked)
        bottom_bar.addWidget(self.btn_retry)

        layout.addLayout(bottom_bar)

    def populate_results(self, summary: BatchSummary, jobs: list[DownloadJob]) -> None:
        """Render completed jobs and highlight low-confidence rows."""
        self.jobs = jobs
        self.lbl_stats.setText(
            f"Results: {summary.downloaded} Downloaded  |  {summary.skipped} Skipped  |  "
            f"{summary.not_found} Not Found  |  {summary.failed} Failed  "
            f"({summary.duration_seconds:.1f} s)"
        )

        failed_jobs = [j for j in jobs if j.status in ("failed", "not_found")]
        self.btn_retry.setText(f"Retry Failed ({len(failed_jobs)}) ↺")
        self.btn_retry.setEnabled(len(failed_jobs) > 0)

        self.table.setRowCount(len(jobs))
        for row, job in enumerate(jobs):
            item_art = QTableWidgetItem(job.song.artist or "Unknown")
            item_tit = QTableWidgetItem(job.song.title)
            item_st = QTableWidgetItem(job.status.value)

            conf_str = "None"
            score_str = ""
            if job.match_decision:
                conf_str = job.match_decision.confidence.value
                score_str = f"{job.match_decision.score:.2f}"

            item_conf = QTableWidgetItem(f"{conf_str.upper()} ({score_str})" if score_str else conf_str.upper())

            # Highlight colors
            if job.status.value == "done":
                item_st.setForeground(Qt.GlobalColor.green)
            elif job.status.value == "failed":
                item_st.setForeground(Qt.GlobalColor.red)
            elif job.status.value == "not_found":
                item_st.setForeground(Qt.GlobalColor.darkYellow)

            # Highlight low confidence rows
            is_low_conf = job.match_decision and job.match_decision.confidence == Confidence.LOW
            if is_low_conf:
                item_conf.setForeground(Qt.GlobalColor.yellow)

            match_text = job.output_path or job.error_message or ""
            item_match = QTableWidgetItem(match_text)

            self.table.setItem(row, 0, item_art)
            self.table.setItem(row, 1, item_tit)
            self.table.setItem(row, 2, item_st)
            self.table.setItem(row, 3, item_conf)
            self.table.setItem(row, 4, item_match)

            # Swap candidate button for low-confidence rows
            if is_low_conf and self.fetch_candidates_func:
                btn_swap = QPushButton("Swap Candidate")
                btn_swap.setObjectName("secondaryButton")
                curr_job = job
                btn_swap.clicked.connect(lambda _, j=curr_job: self._swap_candidate_dialog(j))
                self.table.setCellWidget(row, 5, btn_swap)

    def _swap_candidate_dialog(self, job: DownloadJob) -> None:
        if not self.fetch_candidates_func:
            return
        candidates = self.fetch_candidates_func(job.id)
        if not candidates:
            return
        dialog = CandidateSwapDialog(self, job.song.title, candidates)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_candidate:
            cand = dialog.selected_candidate
            if job.match_decision:
                job.match_decision.candidate = cand
                job.match_decision.confidence = Confidence.HIGH
            # Retry just this job
            self.on_retry_failed([job])

    def _retry_failed_clicked(self) -> None:
        failed_jobs = [j for j in self.jobs if j.status in ("failed", "not_found")]
        if failed_jobs:
            self.on_retry_failed(failed_jobs)

    def _export_csv(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Report CSV", "batch_report.csv", "CSV Files (*.csv)")
        if not file_path:
            return
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Title", "Artist", "Status", "Confidence", "Score", "Output Path", "Details"])
            for j in self.jobs:
                conf = j.match_decision.confidence.value if j.match_decision else "none"
                sc = f"{j.match_decision.score:.2f}" if j.match_decision else "0.00"
                writer.writerow([j.song.title, j.song.artist or "", j.status.value, conf, sc, j.output_path or "", j.error_message or ""])

    def _open_output_folder(self) -> None:
        p = Path(self.output_dir)
        if p.is_dir():
            if os.name == "nt":
                os.startfile(str(p))
            else:
                subprocess.run(["xdg-open", str(p)], check=False)
