"""Thread-safe bridge between the dedicated asyncio worker thread and the Qt UI thread."""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import threading
from typing import Any, Coroutine, TypeVar

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from app.core.events import BatchProgressEvent, JobProgressEvent, JobStatusEvent
from app.core.models import BatchSummary

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AsyncWorkerThread(QThread):
    """Dedicated background thread hosting the asyncio event loop."""

    def __init__(self) -> None:
        super().__init__()
        self.loop: asyncio.AbstractEventLoop | None = None
        self._started_event = threading.Event()

    def run(self) -> None:
        """Run the asyncio event loop in this background worker thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._started_event.set()
        logger.info("Asyncio event loop started on background thread %s", threading.get_ident())
        self.loop.run_forever()
        # Clean up pending tasks
        try:
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
        finally:
            self.loop.close()
            logger.info("Asyncio event loop closed")

    def wait_started(self, timeout: float = 5.0) -> None:
        """Wait until the event loop is fully initialized."""
        self._started_event.wait(timeout)

    def submit(self, coro: Coroutine[Any, Any, T]) -> concurrent.futures.Future[T]:
        """Submit a coroutine thread-safely from the Qt UI thread to the asyncio thread."""
        if not self.loop or not self.loop.is_running():
            raise RuntimeError("Asyncio background worker thread is not running.")
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def stop(self) -> None:
        """Stop the event loop gracefully."""
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.wait(3000)


class QtBridge(QObject):
    """Translates pipeline domain events into throttled 5 Hz Qt signals."""

    # Qt Signals
    job_status_changed = Signal(str, str, str, str)  # (job_id, status_val, error, output_path)
    job_progress_changed = Signal(str, int, int, float)  # (job_id, bytes_down, total_bytes, speed)
    batch_progress_changed = Signal(str, int, int, int, int, int, int, int, float)  # stats
    batch_finished = Signal(object)  # BatchSummary
    toast_requested = Signal(str, str)  # (title, message)
    resume_jobs_requested = Signal(list)  # list[DownloadJob]

    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self._pending_job_statuses: dict[str, tuple[str, str, str]] = {}
        self._pending_job_progress: dict[str, tuple[int, int | None, float]] = {}
        self._pending_batch_progress: BatchProgressEvent | None = None

        # 5 Hz throttle timer running on the Qt event loop
        self._timer = QTimer(self)
        self._timer.setInterval(200)  # 200 ms = 5 Hz
        self._timer.timeout.connect(self._flush_throttled_events)
        self._timer.start()

    def on_job_status_event(self, ev: JobStatusEvent) -> None:
        with self._lock:
            self._pending_job_statuses[ev.job_id] = (
                ev.status.value,
                ev.error_message or "",
                ev.output_path or "",
            )

    def on_job_progress_event(self, ev: JobProgressEvent) -> None:
        with self._lock:
            self._pending_job_progress[ev.job_id] = (
                ev.bytes_downloaded,
                ev.total_bytes,
                ev.speed_bps,
            )

    def on_batch_progress_event(self, ev: BatchProgressEvent) -> None:
        with self._lock:
            self._pending_batch_progress = ev

    def notify_batch_finished(self, summary: BatchSummary) -> None:
        self.batch_finished.emit(summary)

    def request_toast(self, title: str, message: str) -> None:
        self.toast_requested.emit(title, message)

    def _flush_throttled_events(self) -> None:
        """Executed on Qt event loop at 5 Hz to update UI without freezing."""
        with self._lock:
            status_copy = dict(self._pending_job_statuses)
            self._pending_job_statuses.clear()

            progress_copy = dict(self._pending_job_progress)
            self._pending_job_progress.clear()

            batch_ev = self._pending_batch_progress
            self._pending_batch_progress = None

        for job_id, (st, err, out_p) in status_copy.items():
            self.job_status_changed.emit(job_id, st, err, out_p)

        for job_id, (down, total, spd) in progress_copy.items():
            self.job_progress_changed.emit(job_id, down, total or 0, spd)

        if batch_ev:
            self.batch_progress_changed.emit(
                batch_ev.batch_id,
                batch_ev.total,
                batch_ev.completed,
                batch_ev.downloaded,
                batch_ev.skipped,
                batch_ev.not_found,
                batch_ev.failed,
                batch_ev.active_downloads,
                batch_ev.total_speed_bps,
            )
