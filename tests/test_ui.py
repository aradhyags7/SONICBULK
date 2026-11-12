"""Unit and widget tests for PySide6 desktop views."""

import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QProgressBar

from app.core.config import AppSettings
from app.core.models import (
    BatchSummary,
    Candidate,
    Confidence,
    DownloadJob,
    MatchDecision,
    SongEntry,
)
from app.ui.main_window import MainWindow
from app.ui.views.import_view import ImportView
from app.ui.views.progress_view import ProgressView
from app.ui.views.results_view import ResultsView
from app.ui.views.review_view import ReviewView
from app.ui.views.settings_view import SettingsView

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app  # type: ignore[return-value]


def test_import_view_parse(qapp: QApplication) -> None:
    parsed_req: list[tuple[Path | None, str, str]] = []

    def on_parse(p: Path | None, text: str, out_d: str) -> None:
        parsed_req.append((p, text, out_d))

    view = ImportView(default_output_dir="/music", on_parse_requested=on_parse)
    view.paste_box.setPlainText("Queen - Bohemian Rhapsody\nThe Beatles - Let It Be")
    view._on_start_clicked()

    assert len(parsed_req) == 1
    assert "Queen" in parsed_req[0][1]


def test_review_view_interactions(qapp: QApplication) -> None:
    songs = [
        SongEntry(raw_text="Queen - Bohemian Rhapsody", artist="Queen", title="Bohemian Rhapsody"),
        SongEntry(raw_text="The Beatles - Let It Be", artist="The Beatles", title="Let It Be", is_duplicate=True),
    ]

    started: list[list[SongEntry]] = []

    def on_start(final_songs: list[SongEntry], autostart: bool) -> None:
        started.append(final_songs)

    view = ReviewView(on_start_download=on_start, on_back=lambda: None)
    view.populate(songs)

    assert view.table.rowCount() == 2

    # Add row
    view._add_row()
    assert view.table.rowCount() == 3

    # Remove duplicates
    view._remove_duplicates()
    assert view.table.rowCount() == 2  # duplicate was removed, added row remains

    # Start download collects rows
    view._on_start_clicked()
    assert len(started) == 1
    assert len(started[0]) == 2


def test_progress_view_updates(qapp: QApplication) -> None:
    view = ProgressView(on_pause_toggled=lambda _: None, on_cancel=lambda: None)
    job = DownloadJob(song=SongEntry(raw_text="Track", title="Track"), batch_id="b-1", id="job-1")
    view.initialize_batch([job])

    assert view.table.rowCount() == 1

    # Update status
    view.update_job_status("job-1", "downloading", error="", output_path="")
    st_item = view.table.item(0, 2)
    assert st_item is not None and st_item.text() == "downloading"

    # Update progress
    view.update_job_progress("job-1", bytes_down=50000, total_bytes=100000, speed_bps=25000.0)
    pbar = view.table.cellWidget(0, 3)
    assert isinstance(pbar, QProgressBar) and pbar.value() == 50

    # Update batch summary
    view.update_batch_progress(
        total=1, completed=1, downloaded=1, skipped=0, not_found=0, failed=0, active=0, total_speed_bps=0.0
    )
    assert view.count_down_lbl.text() == "1"
    assert view.overall_pbar.value() == 100


def test_results_view_report_and_swap(qapp: QApplication) -> None:
    view = ResultsView(
        output_dir="/music",
        on_retry_failed=lambda _: None,
        on_new_import=lambda: None,
        fetch_candidates_func=lambda _: [
            Candidate(provider="mock", source_id="alt-1", title="Better Match", artist="Artist", score=0.92)
        ],
    )
    summary = BatchSummary(
        batch_id="b-1", total=2, downloaded=1, skipped=0, not_found=0, failed=1, duration_seconds=3.2
    )
    job_ok = DownloadJob(song=SongEntry(raw_text="Song 1", title="Song 1"), batch_id="b-1", id="j1")
    job_ok.status = job_ok.status.DONE
    job_low = DownloadJob(song=SongEntry(raw_text="Song 2", title="Song 2"), batch_id="b-1", id="j2")
    job_low.status = job_low.status.FAILED
    job_low.match_decision = MatchDecision(
        candidate=Candidate(provider="mock", source_id="c1", title="Low", artist="A"),
        confidence=Confidence.LOW,
        score=0.60,
        title_similarity=0.6,
        artist_similarity=0.6,
        penalty_applied=0.0,
        reason="Low confidence",
    )

    view.populate_results(summary, [job_ok, job_low])
    assert view.table.rowCount() == 2
    # Verify retry button enabled for 1 failed
    assert view.btn_retry.isEnabled()


def test_settings_view_save(qapp: QApplication, tmp_path: Path) -> None:
    settings = AppSettings(output_dir=str(tmp_path / "out"))
    saved_settings: list[AppSettings] = []

    def on_save(s: AppSettings) -> None:
        saved_settings.append(s)

    view = SettingsView(settings, on_save_settings=on_save, on_back=lambda: None)
    view.spin_download.setValue(10)
    view.combo_layout.setCurrentText("artist_album")
    view._save()

    assert len(saved_settings) == 1
    assert saved_settings[0].download_concurrency == 10
    assert saved_settings[0].folder_layout == "artist_album"


def test_main_window_lifecycle(qapp: QApplication, tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    win = MainWindow(settings_path=settings_file)
    assert win.stack.count() == 5
    assert win.stack.currentIndex() == 0

    # Test settings open
    win._open_settings()
    assert win.stack.currentIndex() == 4

    # Allow async init to settle before exit
    import time
    time.sleep(0.05)
    win._force_exit()


def test_main_window_start_download_flow(qapp: QApplication, tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    win = MainWindow(settings_path=settings_file)

    # 1. Parse text input
    win.import_view.paste_box.setPlainText("Queen - Radio Ga Ga\nDire Straits - Sultans of Swing")
    win.import_view._on_start_clicked()

    assert win.stack.currentIndex() == 1  # ReviewView
    assert win.review_view.table.rowCount() == 2

    # 2. Start download
    win.review_view.btn_start.click()

    assert win.stack.currentIndex() == 2  # ProgressView
    assert win.progress_view.table.rowCount() == 2
    assert len(win.current_jobs) == 2

    import time
    time.sleep(0.05)
    win._force_exit()
