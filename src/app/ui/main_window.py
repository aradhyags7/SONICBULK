"""Main PySide6 Application Window integrating all views, thread-safe bridge, and tray."""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.config import AppSettings, get_default_config_path
from app.core.events import BatchProgressEvent, JobProgressEvent, JobStatusEvent
from app.core.models import BatchSummary, DownloadJob, SongEntry
from app.core.sleep_blocker import SleepBlocker
from app.db.repository import DatabaseRepository
from app.parse.unified import parse_file, parse_text_input
from app.pipeline.engine import PipelineEngine
from app.sources.cache import CachedSourceProvider
from app.sources.chain import ProviderChain
from app.sources.direct import DirectURLProvider
from app.sources.internet_archive import InternetArchiveProvider
from app.sources.jamendo import JamendoProvider
from app.sources.ytdlp_pool import YtDlpWorkerPool
from app.sources.ytdlp_provider import YtDlpProvider
from app.ui.bridge import AsyncWorkerThread, QtBridge
from app.ui.theme import DARK_THEME_QSS
from app.ui.views.import_view import ImportView
from app.ui.views.progress_view import ProgressView
from app.ui.views.results_view import ResultsView
from app.ui.views.review_view import ReviewView
from app.ui.views.settings_view import SettingsView
from app.ui.widgets.toast import ToastNotification
from app.ui.widgets.tray import SystemTrayManager

logger = logging.getLogger(__name__)


class SidebarWidget(QWidget):
    """Left vertical sidebar with editorial branding and step indicators."""

    step_clicked = Signal(int)
    settings_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebarWidget")
        self.setFixedWidth(210)
        self.setStyleSheet("background-color: #121b15; border-right: 1px solid #1c2921;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 36, 20, 28)
        layout.setSpacing(32)

        # App Logo / Title
        logo = QLabel("Music\nDownloader", self)
        logo.setObjectName("sidebarLogo")
        logo.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: 800; line-height: 1.1; border: none; background: transparent;")
        layout.addWidget(logo)

        # Steps Layout
        self.steps_layout = QVBoxLayout()
        self.steps_layout.setSpacing(10)

        self.btn_step1 = self._create_step_btn("(1)   Import", 0)
        self.btn_step2 = self._create_step_btn("(2)   Review", 1)
        self.btn_step3 = self._create_step_btn("(3)   Download", 2)
        self.btn_step4 = self._create_step_btn("(4)   Results", 3)

        self.steps_layout.addWidget(self.btn_step1)
        self.steps_layout.addWidget(self.btn_step2)
        self.steps_layout.addWidget(self.btn_step3)
        self.steps_layout.addWidget(self.btn_step4)

        layout.addLayout(self.steps_layout)
        layout.addStretch()

        # Settings Button at bottom
        self.btn_settings = QPushButton("Settings", self)
        self.btn_settings.setObjectName("sidebarSettingsBtn")
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.btn_settings)

    def _create_step_btn(self, text: str, index: int) -> QPushButton:
        btn = QPushButton(text, self)
        btn.setObjectName("sidebarStepBtn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self.step_clicked.emit(index))
        return btn

    def set_active_step(self, index: int) -> None:
        btns = [self.btn_step1, self.btn_step2, self.btn_step3, self.btn_step4]
        for i, b in enumerate(btns):
            is_active = (i == index)
            b.setProperty("active", "true" if is_active else "false")
            b.style().unpolish(b)
            b.style().polish(b)


class MainWindow(QMainWindow):
    """Main application window coordinating UI screens and background asyncio tasks."""

    def __init__(self, settings_path: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Music Downloader")
        self.resize(1080, 700)
        self.setMinimumSize(880, 600)
        self.setStyleSheet(DARK_THEME_QSS)

        # Settings
        self.settings_path = settings_path or get_default_config_path()
        self.settings = AppSettings.load_from_file(self.settings_path)
        self.settings.validate()

        # Database
        db_path = self.settings_path.parent / "jobs.db"
        self.repo = DatabaseRepository(db_path)

        # Async background worker thread & Qt signal bridge
        self.async_thread = AsyncWorkerThread()
        self.async_thread.start()
        self.async_thread.wait_started()

        self.bridge = QtBridge()
        self.sleep_blocker = SleepBlocker()

        # State tracking
        self.current_batch_id = ""
        self.current_jobs: list[DownloadJob] = []
        self.pipeline_engine: PipelineEngine | None = None
        self.ytdlp_pool: YtDlpWorkerPool | None = None
        self._is_quitting = False

        # Central Widget & Horizontal Layout (Sidebar + Content Stack)
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left Sidebar
        self.sidebar = SidebarWidget(self)
        self.sidebar.step_clicked.connect(self._on_sidebar_step_clicked)
        self.sidebar.settings_clicked.connect(self._open_settings)
        main_layout.addWidget(self.sidebar)

        # Right Content Area (Stacked Screens)
        self.stack = QStackedWidget(self)
        self.stack.setStyleSheet("background-color: #e6e9e1;")
        main_layout.addWidget(self.stack, 1)

        # Build Views
        self.import_view = ImportView(
            default_output_dir=self.settings.output_dir,
            on_parse_requested=self._on_parse_requested,
        )
        self.review_view = ReviewView(
            on_start_download=self._on_start_download,
            on_back=lambda: self.stack.setCurrentIndex(0),
        )
        self.progress_view = ProgressView(
            on_pause_toggled=self._on_pause_toggled,
            on_cancel=self._on_cancel_requested,
        )
        self.results_view = ResultsView(
            output_dir=self.settings.output_dir,
            on_retry_failed=self._on_retry_failed,
            on_new_import=lambda: self.stack.setCurrentIndex(0),
            fetch_candidates_func=self._fetch_candidates_sync,
        )
        self.settings_view = SettingsView(
            settings=self.settings,
            on_save_settings=self._on_save_settings,
            on_back=lambda: self.stack.setCurrentIndex(0),
        )

        self.stack.addWidget(self.import_view)    # Index 0
        self.stack.addWidget(self.review_view)    # Index 1
        self.stack.addWidget(self.progress_view)  # Index 2
        self.stack.addWidget(self.results_view)   # Index 3
        self.stack.addWidget(self.settings_view)  # Index 4

        self.stack.currentChanged.connect(self._on_stack_page_changed)
        self.sidebar.set_active_step(0)

        # System Tray Manager
        self.tray = SystemTrayManager(
            parent=self,
            on_toggle_visible=self._toggle_visibility,
            on_exit=self._force_exit,
        )

        # Wire Bridge signals to UI
        self.bridge.job_status_changed.connect(self.progress_view.update_job_status)
        self.bridge.job_progress_changed.connect(self.progress_view.update_job_progress)
        self.bridge.batch_progress_changed.connect(self._on_batch_progress_update)
        self.bridge.batch_finished.connect(self._on_batch_finished)
        self.bridge.toast_requested.connect(self.show_toast)
        self.bridge.resume_jobs_requested.connect(self._on_startup_resume)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+O"), self, self.import_view._browse_file)
        QShortcut(QKeySequence("Ctrl+,"), self, self._open_settings)
        QShortcut(QKeySequence("Esc"), self, self._on_escape_pressed)

        # Async initialization
        self.async_thread.submit(self._async_init())

    def _on_sidebar_step_clicked(self, step_idx: int) -> None:
        """Allow clicking on sidebar steps if relevant data exists."""
        if step_idx == 0:
            self.stack.setCurrentIndex(0)
        elif step_idx == 1 and self.review_view.songs:
            self.stack.setCurrentIndex(1)
        elif step_idx == 2 and self.current_jobs:
            self.stack.setCurrentIndex(2)
        elif step_idx == 3 and self.results_view.jobs:
            self.stack.setCurrentIndex(3)

    def _on_stack_page_changed(self, index: int) -> None:
        """Update active pill indicator in sidebar."""
        self.sidebar.set_active_step(index if index < 4 else -1)

    async def _async_init(self) -> None:
        """Initialize database and check for startup recovery."""
        await self.repo.initialize()
        unfinished = await self.repo.get_unfinished_jobs()
        if unfinished and self.settings.auto_resume_on_startup:
            logger.info("Found %d unfinished jobs from previous session; auto-resuming", len(unfinished))
            self.bridge.request_toast("Startup Recovery", f"Resuming {len(unfinished)} unfinished downloads...")
            self.bridge.resume_jobs_requested.emit(unfinished)

    def _on_startup_resume(self, jobs: list[DownloadJob]) -> None:
        """Handle startup recovery on the main Qt thread."""
        self.current_jobs = jobs
        self.current_batch_id = jobs[0].batch_id
        self.progress_view.initialize_batch(jobs)
        self.stack.setCurrentIndex(2)
        self.async_thread.submit(self._run_pipeline(self.current_batch_id, jobs))

    def _on_parse_requested(self, file_path: Path | None, pasted_text: str, output_dir: str) -> None:
        """Parse input and move to Review screen."""
        if output_dir:
            self.settings.output_dir = output_dir

        try:
            if file_path and file_path.is_file():
                doc = parse_file(file_path)
            elif pasted_text:
                doc = parse_text_input(pasted_text)
            else:
                self.show_toast("Import Error", "Please drop a file or paste song names.")
                return

            if not doc.songs:
                self.show_toast("Import Warning", "No songs detected in the provided input.")
                return

            self.review_view.populate_songs(doc.songs)
            self.stack.setCurrentIndex(1)  # Show ReviewView
        except Exception as e:
            logger.exception("Parse failed: %s", e)
            self.show_toast("Parse Error", f"Failed to parse input: {e}")

    def _on_start_download(self, songs: list[SongEntry], auto_start: bool = False) -> None:
        """Prepare batch jobs and transition to download screen."""
        if not songs:
            return

        self.current_batch_id = str(uuid.uuid4())[:8]
        now = time.time()
        self.current_jobs = [
            DownloadJob(
                id=str(uuid.uuid4()),
                song=s,
                batch_id=self.current_batch_id,
                created_at=now,
                updated_at=now,
            )
            for s in songs
        ]

        # Initialize progress table and switch view strictly on the main GUI thread
        self.progress_view.initialize_batch(self.current_jobs)
        self.stack.setCurrentIndex(2)  # Show ProgressView

        self.async_thread.submit(self._start_batch_async(self.current_batch_id, self.current_jobs))

    async def _start_batch_async(self, batch_id: str, jobs: list[DownloadJob]) -> None:
        try:
            if self.repo._conn is None:
                await self.repo.initialize()
            await self.repo.create_batch_from_jobs(batch_id, jobs)
            await self._run_pipeline(batch_id, jobs)
        except Exception as e:
            logger.exception("Batch pipeline failed: %s", e)
            self.bridge.request_toast("Error", f"Download failed: {e}")

    async def _run_pipeline(self, batch_id: str, jobs: list[DownloadJob]) -> None:
        """Build provider chain and run pipeline in asyncio thread."""
        if self.settings.prevent_sleep:
            self.sleep_blocker.enable()

        providers = [
            InternetArchiveProvider(),
            JamendoProvider(client_id=self.settings.jamendo_client_id),
            DirectURLProvider(),
        ]
        if self.settings.ytdlp_enabled:
            if self.ytdlp_pool is None:
                self.ytdlp_pool = YtDlpWorkerPool(pool_size=2)
                await self.ytdlp_pool.start()
            providers.insert(0, YtDlpProvider(pool=self.ytdlp_pool, enabled=True))

        chain = ProviderChain(providers)
        cached_provider = CachedSourceProvider(chain, repository=self.repo, ttl_hours=self.settings.cache_ttl_hours)

        # Pipe events to Qt bridge
        from app.core.events import EventBus
        bus = EventBus()
        bus.subscribe(JobStatusEvent, lambda ev: self.bridge.on_job_status_event(ev) if isinstance(ev, JobStatusEvent) else None)
        bus.subscribe(JobProgressEvent, lambda ev: self.bridge.on_job_progress_event(ev) if isinstance(ev, JobProgressEvent) else None)
        bus.subscribe(BatchProgressEvent, lambda ev: self.bridge.on_batch_progress_event(ev) if isinstance(ev, BatchProgressEvent) else None)

        self.pipeline_engine = PipelineEngine(
            settings=self.settings,
            repository=self.repo,
            provider=cached_provider,
            event_bus=bus,
        )
        await self.pipeline_engine.initialize()

        try:
            summary = await self.pipeline_engine.run_batch(batch_id, jobs)
            self.bridge.notify_batch_finished(summary)
        finally:
            if self.settings.prevent_sleep:
                self.sleep_blocker.disable()

    def _on_batch_progress_update(
        self,
        batch_id: str,
        total: int,
        completed: int,
        downloaded: int,
        skipped: int,
        not_found: int,
        failed: int,
        active: int,
        total_speed_bps: float,
    ) -> None:
        self.progress_view.update_batch_progress(
            total=total,
            completed=completed,
            downloaded=downloaded,
            skipped=skipped,
            not_found=not_found,
            failed=failed,
            active=active,
            total_speed_bps=total_speed_bps,
        )
        self.tray.update_tooltip(completed, total, total_speed_bps)

    def _on_batch_finished(self, summary_obj: object) -> None:
        summary = summary_obj if isinstance(summary_obj, BatchSummary) else BatchSummary(
            batch_id="", total=0, downloaded=0, skipped=0, not_found=0, failed=0, duration_seconds=0.0
        )
        self.results_view.populate_results(summary, self.current_jobs)
        self.stack.setCurrentIndex(3)  # Show ResultsView
        self.tray.notify_completion(summary.downloaded, summary.not_found, summary.failed)
        self.show_toast("Batch Complete", f"{summary.downloaded} downloaded, {summary.failed} failed.")

    def _on_retry_failed(self, failed_jobs: list[DownloadJob]) -> None:
        """One-click retry of failed or not found songs."""
        songs = [j.song for j in failed_jobs]
        self._on_start_download(songs, auto_start=False)

    def _on_pause_toggled(self, is_paused: bool) -> None:
        if self.pipeline_engine:
            if is_paused:
                self.pipeline_engine.pause()
            else:
                self.pipeline_engine.resume()

    def _on_cancel_requested(self) -> None:
        if self.pipeline_engine:
            self.pipeline_engine.cancel()
            self.show_toast("Cancelled", "Cancelling remaining downloads safely...")

    def _fetch_candidates_sync(self, job_id: str) -> list:
        future = self.async_thread.submit(self.repo.get_candidates(job_id))
        try:
            return future.result(timeout=2.0)
        except Exception:
            return []

    def _open_settings(self) -> None:
        self.stack.setCurrentIndex(4)

    def _on_save_settings(self, new_settings: AppSettings) -> None:
        self.settings = new_settings
        self.settings.save_to_file(self.settings_path)
        self.show_toast("Settings Saved", "Preferences updated successfully.")
        self.stack.setCurrentIndex(0)

    def show_toast(self, title: str, message: str) -> None:
        toast = ToastNotification(self, title, message)
        toast.show_toast()

    def _toggle_visibility(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()

    def _on_escape_pressed(self) -> None:
        if self.stack.currentIndex() != 0:
            self.stack.setCurrentIndex(0)

    def _force_exit(self) -> None:
        self._is_quitting = True
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event with graceful shutdown within 3 seconds."""
        if not self._is_quitting and self.pipeline_engine and self.pipeline_engine.active_downloads_count > 0:
            reply = QMessageBox.question(
                self,
                "Active Downloads",
                "Downloads are currently in progress. Do you want to minimize to the system tray instead of exiting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.hide()
                event.ignore()
                return

        # Perform graceful shutdown within 3 seconds
        logger.info("Initiating graceful shutdown...")
        if self.pipeline_engine:
            self.pipeline_engine.cancel()

        if self.settings.prevent_sleep:
            self.sleep_blocker.disable()

        # Stop background thread and close resources
        if self.pipeline_engine:
            try:
                self.async_thread.submit(self.pipeline_engine.close()).result(timeout=1.0)
            except Exception:
                pass
        if self.ytdlp_pool:
            try:
                self.async_thread.submit(self.ytdlp_pool.close()).result(timeout=1.0)
            except Exception:
                pass
        try:
            self.async_thread.submit(self.repo.close()).result(timeout=1.0)
        except Exception:
            pass
        self.async_thread.stop()

        event.accept()
