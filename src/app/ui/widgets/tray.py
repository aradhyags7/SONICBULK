"""System tray integration with progress tooltip and completion notifications."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget


def create_default_icon() -> QIcon:
    """Generate a clean vector icon programmatically."""
    pix = QPixmap(32, 32)
    pix.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#2563eb"))
    painter.setPen(QColor("#1d4ed8"))
    painter.drawRoundedRect(2, 2, 28, 28, 6, 6)

    # Draw music note
    painter.setPen(QColor("#ffffff"))
    painter.setBrush(QColor("#ffffff"))
    painter.drawEllipse(8, 18, 6, 6)
    painter.drawEllipse(18, 15, 6, 6)
    painter.drawLine(14, 21, 14, 8)
    painter.drawLine(24, 18, 24, 6)
    painter.drawLine(14, 8, 24, 6)
    painter.end()
    return QIcon(pix)


class SystemTrayManager(QObject):
    """Manages the system tray icon, progress tooltip, and background notifications."""

    def __init__(
        self,
        parent: QWidget,
        on_toggle_visible: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self.parent_window = parent
        self.on_toggle_visible = on_toggle_visible
        self.on_exit = on_exit

        self.tray_icon = QSystemTrayIcon(create_default_icon(), parent)
        self.tray_icon.setToolTip("Music Downloader - Idle")

        menu = QMenu(parent)
        self.action_show = QAction("Show / Hide", parent)
        self.action_show.triggered.connect(self.on_toggle_visible)
        menu.addAction(self.action_show)

        menu.addSeparator()

        self.action_exit = QAction("Exit", parent)
        self.action_exit.triggered.connect(self.on_exit)
        menu.addAction(self.action_exit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)

        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.on_toggle_visible()

    def update_tooltip(self, completed: int, total: int, speed_bps: float) -> None:
        if total > 0:
            pct = (completed / total) * 100
            speed_mb = speed_bps / (1024 * 1024)
            tip = f"Music Downloader: {completed}/{total} ({pct:.0f}%) - {speed_mb:.1f} MB/s"
        else:
            tip = "Music Downloader - Idle"
        self.tray_icon.setToolTip(tip)

    def notify_completion(self, downloaded: int, not_found: int, failed: int) -> None:
        """Trigger OS notification on batch completion."""
        msg = f"{downloaded} downloaded, {not_found} not found, {failed} failed"
        self.tray_icon.showMessage(
            "Batch Download Finished",
            msg,
            QSystemTrayIcon.MessageIcon.Information,
            5000,
        )
