"""Non-blocking toast notifications that fade in and out."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QVBoxLayout, QWidget


class ToastNotification(QWidget):
    """Floating non-blocking notification pill."""

    def __init__(self, parent: QWidget | None, title: str, message: str, duration_ms: int = 3500) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)

        container = QWidget(self)
        container.setStyleSheet(
            "background-color: #1f242d; border: 1px solid #3b82f6; border-radius: 8px;"
        )
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(12, 8, 12, 8)
        c_layout.setSpacing(4)

        title_lbl = QLabel(title, container)
        title_lbl.setStyleSheet("color: #60a5fa; font-weight: bold; font-size: 13px; border: none; background: transparent;")

        msg_lbl = QLabel(message, container)
        msg_lbl.setStyleSheet("color: #e2e8f0; font-size: 12px; border: none; background: transparent;")
        msg_lbl.setWordWrap(True)

        c_layout.addWidget(title_lbl)
        c_layout.addWidget(msg_lbl)
        layout.addWidget(container)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_anim = QPropertyAnimation(self.opacity_effect, b"opacity")

        self.adjustSize()
        self._position_toast()

        # Auto-dismiss timer
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(duration_ms)
        self.timer.timeout.connect(self._fade_out)

    def _position_toast(self) -> None:
        p = self.parentWidget()
        if p is not None:
            p_geom = p.rect()
            x = p_geom.width() - self.width() - 24
            y = p_geom.height() - self.height() - 24
            self.move(x, y)

    def show_toast(self) -> None:
        self._position_toast()
        self.show()
        self.opacity_anim.stop()
        self.opacity_anim.setDuration(250)
        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.opacity_anim.start()
        self.timer.start()

    def _fade_out(self) -> None:
        self.opacity_anim.stop()
        self.opacity_anim.setDuration(350)
        self.opacity_anim.setStartValue(1.0)
        self.opacity_anim.setEndValue(0.0)
        self.opacity_anim.finished.connect(self.deleteLater)
        self.opacity_anim.start()
