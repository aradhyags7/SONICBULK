"""Review screen allowing inspection, editing, and deduplication of parsed songs."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
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

from app.core.models import SongEntry


class ReviewView(QWidget):
    """Review screen matching custom design with white card table and lime CTA."""

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
        layout.setContentsMargins(40, 36, 40, 36)
        layout.setSpacing(16)

        # Top Header Bar
        top_bar = QHBoxLayout()
        self.title_label = QLabel("0 songs found", self)
        self.title_label.setStyleSheet("font-size: 32px; font-weight: 800; color: #111813; letter-spacing: -0.5px;")
        top_bar.addWidget(self.title_label)

        top_bar.addStretch()

        self.duplicate_badge = QLabel("0 duplicates", self)
        self.duplicate_badge.setStyleSheet(
            "background-color: #fce7d8; color: #b45309; padding: 5px 12px; border-radius: 12px; font-weight: 600; font-size: 12px;"
        )
        self.duplicate_badge.setVisible(False)
        top_bar.addWidget(self.duplicate_badge)

        self.btn_remove_dups = QPushButton("Remove duplicates", self)
        self.btn_remove_dups.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_remove_dups.clicked.connect(self._remove_duplicates)
        self.btn_remove_dups.setVisible(False)
        top_bar.addWidget(self.btn_remove_dups)

        layout.addLayout(top_bar)

        # Informational Banner
        self.banner = QFrame(self)
        self.banner.setStyleSheet(
            "background-color: #edf7a5; border-radius: 8px; padding: 10px 14px; border: none;"
        )
        banner_layout = QHBoxLayout(self.banner)
        banner_layout.setContentsMargins(10, 8, 10, 8)
        self.lbl_banner_text = QLabel(
            "No artists detected. Add one where you can and matches get more accurate.", self.banner
        )
        self.lbl_banner_text.setStyleSheet("color: #273815; font-size: 13px; font-weight: 500; border: none; background: transparent;")
        banner_layout.addWidget(self.lbl_banner_text)
        layout.addWidget(self.banner)

        # White Card Container for Table
        table_card = QFrame(self)
        table_card.setObjectName("whiteCard")
        table_card.setStyleSheet("background-color: #ffffff; border: 1px solid #d8ddcf; border-radius: 16px; padding: 8px;")
        t_layout = QVBoxLayout(table_card)
        t_layout.setContentsMargins(4, 4, 4, 4)

        self.table = QTableWidget(table_card)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["#", "TITLE", "ARTIST", "SEARCH QUERY", "STATUS"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.cellChanged.connect(self._on_cell_changed)
        t_layout.addWidget(self.table)

        layout.addWidget(table_card, 1)

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(0, 8, 0, 0)

        self.btn_back = QPushButton("← Back", self)
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setMinimumHeight(42)
        self.btn_back.clicked.connect(self.on_back)
        bottom_bar.addWidget(self.btn_back)

        bottom_bar.addStretch()

        self.chk_autostart = QCheckBox("Auto-start next time", self)
        self.chk_autostart.setCursor(Qt.CursorShape.PointingHandCursor)
        bottom_bar.addWidget(self.chk_autostart)

        self.btn_start = QPushButton("Start download", self)
        self.btn_start.setObjectName("primaryLimeBtn")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setMinimumHeight(44)
        self.btn_start.setStyleSheet("font-size: 14px; padding: 10px 24px;")
        self.btn_start.clicked.connect(self._on_start_clicked)
        bottom_bar.addWidget(self.btn_start)

        layout.addLayout(bottom_bar)

    def populate_songs(self, songs: list[SongEntry]) -> None:
        """Load parsed songs into editable table."""
        self.songs = list(songs)
        self.table.blockSignals(True)
        self.table.setRowCount(len(songs))

        missing_artists_count = 0
        duplicate_count = 0

        for row, s in enumerate(songs):
            # Column 0: Index #
            idx_item = QTableWidgetItem(str(row + 1))
            idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            idx_item.setFlags(idx_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            idx_item.setForeground(Qt.GlobalColor.darkGray)

            # Column 1: Title
            tit_item = QTableWidgetItem(s.title)
            font = tit_item.font()
            font.setBold(True)
            tit_item.setFont(font)
            tit_item.setForeground(Qt.GlobalColor.black)

            # Column 2: Artist
            if s.artist:
                art_item = QTableWidgetItem(s.artist)
                art_item.setForeground(Qt.GlobalColor.black)
            else:
                missing_artists_count += 1
                art_item = QTableWidgetItem("Add artist")
                art_item.setForeground(Qt.GlobalColor.gray)

            # Column 3: Search Query
            query_item = QTableWidgetItem(s.query or s.title)
            query_item.setForeground(Qt.GlobalColor.darkGray)

            # Column 4: Status
            if s.is_duplicate:
                duplicate_count += 1
                st_item = QTableWidgetItem("Duplicate")
                st_item.setForeground(Qt.GlobalColor.darkYellow)
            else:
                st_item = QTableWidgetItem("Ready")
                st_item.setForeground(Qt.GlobalColor.darkGreen)
            st_item.setFlags(st_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.table.setItem(row, 0, idx_item)
            self.table.setItem(row, 1, tit_item)
            self.table.setItem(row, 2, art_item)
            self.table.setItem(row, 3, query_item)
            self.table.setItem(row, 4, st_item)

        self.table.blockSignals(False)

        # Update Header and Badge
        self.title_label.setText(f"{len(songs)} songs found")
        active_count = len(songs) - duplicate_count
        self.btn_start.setText(f"Start download · {active_count} songs")

        if duplicate_count > 0:
            self.duplicate_badge.setText(f"{duplicate_count} duplicate{'s' if duplicate_count > 1 else ''}")
            self.duplicate_badge.setVisible(True)
            self.btn_remove_dups.setVisible(True)
        else:
            self.duplicate_badge.setVisible(False)
            self.btn_remove_dups.setVisible(False)

        # Banner visibility
        if missing_artists_count > len(songs) * 0.4:
            self.lbl_banner_text.setText("No artists detected on some songs. Add one where you can and matches get more accurate.")
            self.banner.setVisible(True)
        else:
            self.banner.setVisible(False)

    def populate(self, songs: list[SongEntry]) -> None:
        """Alias for compatibility with tests."""
        self.populate_songs(songs)

    def _add_row(self) -> None:
        """Add a blank row to table for manual entry."""
        new_song = SongEntry(raw_text="New Track", title="New Track")
        self.songs.append(new_song)
        self.populate_songs(self.songs)

    def _on_cell_changed(self, row: int, col: int) -> None:
        if row < 0 or row >= len(self.songs):
            return
        song = self.songs[row]
        item = self.table.item(row, col)
        if not item:
            return

        text = item.text().strip()
        if col == 1:
            song.title = text
            self._update_query_for_song(row, song)
        elif col == 2:
            if text and text != "Add artist":
                song.artist = text
            else:
                song.artist = None
            self._update_query_for_song(row, song)
        elif col == 3:
            song.query = text

    def _update_query_for_song(self, row: int, song: SongEntry) -> None:
        if song.artist:
            song.query = f"{song.artist} - {song.title}"
        else:
            song.query = song.title
        q_item = self.table.item(row, 3)
        if q_item:
            self.table.blockSignals(True)
            q_item.setText(song.query)
            self.table.blockSignals(False)

    def _remove_duplicates(self) -> None:
        self.songs = [s for s in self.songs if not s.is_duplicate]
        self.populate_songs(self.songs)

    def _on_start_clicked(self) -> None:
        auto = self.chk_autostart.isChecked()
        self.on_start_download(self.songs, auto)
