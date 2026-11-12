"""Results and final audit report screen with metric cards and candidate swapping."""

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
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.models import BatchSummary, Candidate, Confidence, DownloadJob


class CandidateSwapDialog(QDialog):
    """Modal dialog allowing the user to select an alternative candidate for a match."""

    def __init__(self, parent: QWidget, song_title: str, candidates: list[Candidate]) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Swap Candidate: {song_title}")
        self.resize(650, 360)
        self.setStyleSheet("background-color: #e6e9e1; color: #111813;")
        self.selected_candidate: Candidate | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        lbl = QLabel(f"Available candidates for '{song_title}':", self)
        lbl.setStyleSheet("font-weight: 800; font-size: 16px; color: #111813;")
        layout.addWidget(lbl)

        table_card = QFrame(self)
        table_card.setStyleSheet("background-color: #ffffff; border: 1px solid #d8ddcf; border-radius: 12px; padding: 6px;")
        t_layout = QVBoxLayout(table_card)

        self.table = QTableWidget(table_card)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["TITLE", "ARTIST", "SCORE", "DURATION"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)

        self.table.setRowCount(len(candidates))
        for row, c in enumerate(candidates):
            self.table.setItem(row, 0, QTableWidgetItem(c.title))
            self.table.setItem(row, 1, QTableWidgetItem(c.artist or "Unknown"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{c.score:.2f}"))
            dur_str = f"{int(c.duration_seconds // 60)}:{int(c.duration_seconds % 60):02d}" if c.duration_seconds else "--:--"
            self.table.setItem(row, 3, QTableWidgetItem(dur_str))

        t_layout.addWidget(self.table)
        layout.addWidget(table_card, 1)

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.clicked.connect(self.reject)

        btn_select = QPushButton("Use this candidate", self)
        btn_select.setObjectName("primaryLimeBtn")
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


class UnsureSongRow(QWidget):
    """Row item in the Worth a Listen card."""

    def __init__(
        self,
        job: DownloadJob,
        on_swap_clicked: Callable[[DownloadJob], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(12)

        matched_title = ""
        score_val = 0.50
        if job.match_decision and job.match_decision.candidate:
            matched_title = job.match_decision.candidate.title
            score_val = job.match_decision.score

        text_lbl = QLabel(f"<b>{job.song.title}</b> &nbsp;<span style='color: #64748b;'>matched “{matched_title}”</span>", self)
        text_lbl.setStyleSheet("font-size: 13px; color: #111813; border: none; background: transparent;")
        layout.addWidget(text_lbl, 1)

        badge = QLabel(f"Low match · {score_val:.2f}", self)
        badge.setStyleSheet(
            "background-color: #fce7d8; color: #b45309; border-radius: 10px; font-weight: 600; font-size: 11px; padding: 4px 10px; border: none;"
        )
        layout.addWidget(badge)

        if job.output_path and Path(job.output_path).is_file():
            btn_play = QPushButton("Play", self)
            btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_play.clicked.connect(lambda: self._play_file(job.output_path))
            layout.addWidget(btn_play)

        btn_swap = QPushButton("Swap", self)
        btn_swap.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_swap.clicked.connect(lambda: on_swap_clicked(job))
        layout.addWidget(btn_swap)

    def _play_file(self, path: str | None) -> None:
        if path and Path(path).is_file():
            if os.name == "nt":
                os.startfile(path)
            else:
                subprocess.run(["xdg-open", path], check=False)


class ResultsView(QWidget):
    """Final summary report screen matching the custom design."""

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

        # Compatibility table for tests & headless reports
        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 36, 40, 36)
        layout.setSpacing(20)

        # Header: Title & Subtitle + Open Folder Button
        header_row = QHBoxLayout()

        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        self.lbl_title = QLabel("Done. 0 songs in your folder.", self)
        self.lbl_title.setStyleSheet("font-size: 32px; font-weight: 800; color: #111813; letter-spacing: -0.5px;")
        self.lbl_subtitle = QLabel(f"0s · {self.output_dir}", self)
        self.lbl_subtitle.setStyleSheet("color: #556052; font-size: 14px; font-weight: 500;")
        title_col.addWidget(self.lbl_title)
        title_col.addWidget(self.lbl_subtitle)
        header_row.addLayout(title_col)

        header_row.addStretch()

        btn_open = QPushButton("Open folder", self)
        btn_open.setObjectName("primaryLimeBtn")
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setMinimumHeight(42)
        btn_open.clicked.connect(self._open_output_folder)
        header_row.addWidget(btn_open)

        layout.addLayout(header_row)

        # 4 Big Stat Cards Row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)

        # Card 1: Downloaded (Dark Card)
        card_down = QFrame(self)
        card_down.setObjectName("darkHeroCard")
        card_down.setStyleSheet("background-color: #141f17; border-radius: 16px; padding: 20px; border: none;")
        cd_layout = QVBoxLayout(card_down)
        cd_layout.setSpacing(6)
        self.lbl_num_downloaded = QLabel("0", card_down)
        self.lbl_num_downloaded.setStyleSheet("color: #c8f53c; font-size: 44px; font-weight: 800; border: none; background: transparent;")
        lbl_cd_name = QLabel("Downloaded", card_down)
        lbl_cd_name.setStyleSheet("color: #c8f53c; font-size: 13px; font-weight: 700; border: none; background: transparent;")
        cd_layout.addWidget(self.lbl_num_downloaded)
        cd_layout.addWidget(lbl_cd_name)
        cards_row.addWidget(card_down, 1)

        # Card 2: Skipped (White Card)
        card_skip = QFrame(self)
        card_skip.setObjectName("whiteCard")
        card_skip.setStyleSheet("background-color: #ffffff; border: 1px solid #d8ddcf; border-radius: 16px; padding: 20px;")
        cs_layout = QVBoxLayout(card_skip)
        cs_layout.setSpacing(6)
        self.lbl_num_skipped = QLabel("0", card_skip)
        self.lbl_num_skipped.setStyleSheet("color: #111813; font-size: 44px; font-weight: 800; border: none; background: transparent;")
        lbl_cs_name = QLabel("Skipped", card_skip)
        lbl_cs_name.setStyleSheet("color: #64748b; font-size: 13px; font-weight: 600; border: none; background: transparent;")
        cs_layout.addWidget(self.lbl_num_skipped)
        cs_layout.addWidget(lbl_cs_name)
        cards_row.addWidget(card_skip, 1)

        # Card 3: Not found (White Card)
        card_notfound = QFrame(self)
        card_notfound.setObjectName("whiteCard")
        card_notfound.setStyleSheet("background-color: #ffffff; border: 1px solid #d8ddcf; border-radius: 16px; padding: 20px;")
        cnf_layout = QVBoxLayout(card_notfound)
        cnf_layout.setSpacing(6)
        self.lbl_num_notfound = QLabel("0", card_notfound)
        self.lbl_num_notfound.setStyleSheet("color: #111813; font-size: 44px; font-weight: 800; border: none; background: transparent;")
        lbl_cnf_name = QLabel("Not found", card_notfound)
        lbl_cnf_name.setStyleSheet("color: #64748b; font-size: 13px; font-weight: 600; border: none; background: transparent;")
        cnf_layout.addWidget(self.lbl_num_notfound)
        cnf_layout.addWidget(lbl_cnf_name)
        cards_row.addWidget(card_notfound, 1)

        # Card 4: Failed (White Card)
        card_failed = QFrame(self)
        card_failed.setObjectName("whiteCard")
        card_failed.setStyleSheet("background-color: #ffffff; border: 1px solid #d8ddcf; border-radius: 16px; padding: 20px;")
        cf_layout = QVBoxLayout(card_failed)
        cf_layout.setSpacing(6)
        self.lbl_num_failed = QLabel("0", card_failed)
        self.lbl_num_failed.setStyleSheet("color: #111813; font-size: 44px; font-weight: 800; border: none; background: transparent;")
        lbl_cf_name = QLabel("Failed", card_failed)
        lbl_cf_name.setStyleSheet("color: #64748b; font-size: 13px; font-weight: 600; border: none; background: transparent;")
        cf_layout.addWidget(self.lbl_num_failed)
        cf_layout.addWidget(lbl_cf_name)
        cards_row.addWidget(card_failed, 1)

        layout.addLayout(cards_row)

        # Worth A Listen Card Container
        self.unsure_card = QFrame(self)
        self.unsure_card.setObjectName("whiteCard")
        self.unsure_card.setStyleSheet("background-color: #ffffff; border: 1px solid #d8ddcf; border-radius: 16px; padding: 20px;")
        unsure_layout = QVBoxLayout(self.unsure_card)
        unsure_layout.setSpacing(12)

        self.lbl_unsure_header = QLabel("WORTH A LISTEN · SONGS THE APP WAS UNSURE ABOUT", self.unsure_card)
        self.lbl_unsure_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px; border: none; background: transparent;")
        unsure_layout.addWidget(self.lbl_unsure_header)

        self.unsure_rows_container = QVBoxLayout()
        self.unsure_rows_container.setSpacing(6)
        unsure_layout.addLayout(self.unsure_rows_container)
        unsure_layout.addStretch()

        layout.addWidget(self.unsure_card, 1)

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(0, 8, 0, 0)

        self.btn_new = QPushButton("New batch", self)
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.clicked.connect(self.on_new_import)
        bottom_bar.addWidget(self.btn_new)

        bottom_bar.addStretch()

        self.btn_export = QPushButton("Export report CSV", self)
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.clicked.connect(self._export_csv)
        bottom_bar.addWidget(self.btn_export)

        self.btn_retry = QPushButton("Retry failed (0)", self)
        self.btn_retry.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_retry.clicked.connect(self._retry_failed_clicked)
        bottom_bar.addWidget(self.btn_retry)

        layout.addLayout(bottom_bar)

    def populate_results(self, summary: BatchSummary, jobs: list[DownloadJob]) -> None:
        """Populate result metrics and low-confidence review rows."""
        self.jobs = list(jobs)

        # Update compatibility table
        self.table.setRowCount(len(jobs))
        for row, job in enumerate(jobs):
            self.table.setItem(row, 0, QTableWidgetItem(job.song.artist or "Unknown"))
            self.table.setItem(row, 1, QTableWidgetItem(job.song.title))
            self.table.setItem(row, 2, QTableWidgetItem(job.status.value))
            conf = job.match_decision.confidence.value if job.match_decision else "none"
            self.table.setItem(row, 3, QTableWidgetItem(conf))
            self.table.setItem(row, 4, QTableWidgetItem(job.output_path or ""))
            btn_swap = QPushButton("Swap Candidate")
            self.table.setCellWidget(row, 5, btn_swap)

        self.lbl_title.setText(f"Done. {summary.downloaded} songs in your folder.")
        mins = int(summary.duration_seconds // 60)
        secs = int(summary.duration_seconds % 60)
        time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
        self.lbl_subtitle.setText(f"{time_str} · {self.output_dir}")

        self.lbl_num_downloaded.setText(str(summary.downloaded))
        self.lbl_num_skipped.setText(str(summary.skipped))
        self.lbl_num_notfound.setText(str(summary.not_found))
        self.lbl_num_failed.setText(str(summary.failed))

        failed_count = summary.not_found + summary.failed
        self.btn_retry.setText(f"Retry failed ({failed_count})")
        self.btn_retry.setEnabled(failed_count > 0)

        # Clear existing unsure rows
        while self.unsure_rows_container.count() > 0:
            item = self.unsure_rows_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Find low-confidence or non-done tracks
        unsure_jobs = [
            j for j in jobs
            if (j.match_decision and j.match_decision.confidence == Confidence.LOW)
            or j.status.value in ("failed", "not_found")
        ]

        if not unsure_jobs:
            # If all were high confidence, show recently downloaded
            unsure_jobs = [j for j in jobs if j.status.value == "done"][:6]
            self.lbl_unsure_header.setText(f"COMPLETED TRACKS · {len(unsure_jobs)} SONGS")
        else:
            self.lbl_unsure_header.setText(f"WORTH A LISTEN · {len(unsure_jobs)} SONGS THE APP WAS UNSURE ABOUT")

        for job in unsure_jobs[:8]:
            row_w = UnsureSongRow(job, self._swap_candidate_dialog, self.unsure_card)
            self.unsure_rows_container.addWidget(row_w)

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
            self.on_retry_failed([job])

    def _retry_failed_clicked(self) -> None:
        failed_jobs = [j for j in self.jobs if j.status.value in ("failed", "not_found")]
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
