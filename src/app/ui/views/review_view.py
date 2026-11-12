"""Review screen allowing inspection, editing, and deduplication of parsed songs."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.models import SongEntry


class ReviewView(QWidget):
    """Review screen allowing the user to edit or remove lines before starting."""

    def __init__(
        self,
        on_start_download: Callable[[list[SongEntry], bool], None],
        on_back: Callable[[], None],
    ) -> None:
        super().__init__()
        self.on_start_download = on_start_download
        self.on_back = on_back
        self.songs: list[SongEntry] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header bar
        top_bar = QHBoxLayout()
        self.title_label = QLabel("Review Parsed Songs", self)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        self.count_badge = QLabel("0 songs", self)
        self.count_badge.setStyleSheet(
            "background-color: #2563eb; color: #ffffff; padding: 3px 10px; border-radius: 10px; font-weight: bold;"
        )
        top_bar.addWidget(self.title_label)
        top_bar.addWidget(self.count_badge)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # Table of parsed items
        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Artist", "Title", "Search Query", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        # Table management toolbar
        toolbar = QHBoxLayout()
        btn_add = QPushButton("+ Add Row", self)
        btn_add.setObjectName("secondaryButton")
        btn_add.clicked.connect(self._add_row)

        btn_remove = QPushButton("- Remove Selected", self)
        btn_remove.setObjectName("secondaryButton")
        btn_remove.clicked.connect(self._remove_selected)

        btn_remove_dups = QPushButton("Remove Duplicates", self)
        btn_remove_dups.setObjectName("secondaryButton")
        btn_remove_dups.clicked.connect(self._remove_duplicates)

        toolbar.addWidget(btn_add)
        toolbar.addWidget(btn_remove)
        toolbar.addWidget(btn_remove_dups)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()
        btn_back = QPushButton("← Back to Import", self)
        btn_back.setObjectName("secondaryButton")
        btn_back.clicked.connect(self.on_back)
        bottom_bar.addWidget(btn_back)

        bottom_bar.addStretch()

        self.chk_autostart = QCheckBox("Auto-start downloads next time", self)
        bottom_bar.addWidget(self.chk_autostart)

        self.btn_start = QPushButton("Start Download Batch ▶", self)
        self.btn_start.setMinimumHeight(40)
        self.btn_start.setStyleSheet("padding: 10px 24px; font-size: 14px;")
        self.btn_start.clicked.connect(self._on_start_clicked)
        bottom_bar.addWidget(self.btn_start)

        layout.addLayout(bottom_bar)

    def populate(self, songs: list[SongEntry]) -> None:
        """Load parsed songs into the review table."""
        self.songs = songs
        self.table.setRowCount(len(songs))
        dup_count = 0

        for row, s in enumerate(songs):
            item_artist = QTableWidgetItem(s.artist or "")
            item_title = QTableWidgetItem(s.title)
            item_query = QTableWidgetItem(s.query)

            if s.is_duplicate:
                dup_count += 1
                item_status = QTableWidgetItem("Exact Duplicate")
                item_status.setForeground(Qt.GlobalColor.darkRed)
            elif s.near_duplicate_of:
                dup_count += 1
                item_status = QTableWidgetItem("Near-Duplicate")
                item_status.setForeground(Qt.GlobalColor.darkYellow)
            else:
                item_status = QTableWidgetItem("Ready")
                item_status.setForeground(Qt.GlobalColor.green)

            item_status.setFlags(item_status.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.table.setItem(row, 0, item_artist)
            self.table.setItem(row, 1, item_title)
            self.table.setItem(row, 2, item_query)
            self.table.setItem(row, 3, item_status)

        self.count_badge.setText(f"{len(songs)} songs ({dup_count} duplicate)")

    def _add_row(self) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem("New Artist"))
        self.table.setItem(row, 1, QTableWidgetItem("New Song"))
        self.table.setItem(row, 2, QTableWidgetItem("New Artist - New Song"))
        status_item = QTableWidgetItem("Ready")
        status_item.setForeground(Qt.GlobalColor.green)
        status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 3, status_item)
        self.count_badge.setText(f"{self.table.rowCount()} songs")

    def _remove_selected(self) -> None:
        selected_rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for r in selected_rows:
            self.table.removeRow(r)
        self.count_badge.setText(f"{self.table.rowCount()} songs")

    def _remove_duplicates(self) -> None:
        for r in range(self.table.rowCount() - 1, -1, -1):
            st_item = self.table.item(r, 3)
            if st_item and ("Duplicate" in st_item.text()):
                self.table.removeRow(r)
        self.count_badge.setText(f"{self.table.rowCount()} songs")

    def _on_start_clicked(self) -> None:
        # Collect edited songs from table
        final_songs: list[SongEntry] = []
        for r in range(self.table.rowCount()):
            it_art = self.table.item(r, 0)
            art = it_art.text().strip() if it_art else None

            it_tit = self.table.item(r, 1)
            tit = it_tit.text().strip() if it_tit else ""

            it_q = self.table.item(r, 2)
            q = it_q.text().strip() if it_q else ""

            it_st = self.table.item(r, 3)
            st = it_st.text() if it_st else ""
            is_dup = "Duplicate" in st

            if tit:
                final_songs.append(SongEntry(
                    raw_text=f"{art or ''} - {tit}".strip(" -"),
                    title=tit,
                    artist=art or None,
                    query=q or tit,
                    is_duplicate=is_dup,
                ))

        self.on_start_download(final_songs, self.chk_autostart.isChecked())
