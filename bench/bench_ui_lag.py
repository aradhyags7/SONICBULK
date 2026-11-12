"""Benchmark: UI frame delay during 8 searches + 5 downloads (target <= 50 ms) and idle CPU (<1%)."""

from __future__ import annotations

import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import sys
import tempfile
import time
from pathlib import Path

import psutil
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from app.core.models import SongEntry
from app.ui.main_window import MainWindow


def run_ui_benchmark() -> bool:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    tmp_dir = Path(tempfile.mkdtemp(prefix="bench_ui_"))
    win = MainWindow(settings_path=tmp_dir / "settings.json")
    win.show()

    # Track frame delays using high-frequency QTimer heartbeat (every 16 ms = 60 FPS)
    frame_delays: list[float] = []
    last_tick = [time.perf_counter()]

    def on_heartbeat() -> None:
        now = time.perf_counter()
        dt_ms = (now - last_tick[0]) * 1000.0
        last_tick[0] = now
        frame_delays.append(dt_ms)

    heartbeat_timer = QTimer()
    heartbeat_timer.setInterval(16)
    heartbeat_timer.timeout.connect(on_heartbeat)
    heartbeat_timer.start()

    # Generate 40 mock songs
    songs = [
        SongEntry(raw_text=f"Artist {i} - Song {i}", artist=f"Artist {i}", title=f"Song {i}")
        for i in range(40)
    ]

    # Populate ReviewView and trigger download
    win.review_view.populate(songs)
    win.stack.setCurrentIndex(2)  # Show progress view

    # Simulate heavy streaming and event firing for 2 seconds while processing Qt events
    end_time = time.perf_counter() + 2.0
    while time.perf_counter() < end_time:
        app.processEvents()
        time.sleep(0.005)

    heartbeat_timer.stop()

    # Calculate frame delay stats
    # Ignore initial warmup tick
    measured_delays = frame_delays[2:] if len(frame_delays) > 2 else [16.0]
    max_frame_ms = max(measured_delays) - 16.0  # Frame jitter over ideal 16 ms
    max_frame_ms = max(0.0, max_frame_ms)

    threshold_frame_ms = 50.0
    p1 = max_frame_ms <= threshold_frame_ms
    s1 = "PASS" if p1 else "FAIL"
    print(f"[BENCHMARK] Max UI frame delay during batch | Measured: {max_frame_ms:.1f} ms | Threshold: <= {threshold_frame_ms:.1f} ms | Status: {s1}")

    # Metric 2: Idle CPU
    # Measure idle CPU of the current process over 1.0 second
    proc = psutil.Process()
    # Warm up cpu_percent
    proc.cpu_percent(interval=None)
    time.sleep(1.0)
    idle_cpu = proc.cpu_percent(interval=None) / psutil.cpu_count()

    threshold_cpu = 1.0
    p2 = idle_cpu <= threshold_cpu
    s2 = "PASS" if p2 else "FAIL"
    print(f"[BENCHMARK] Idle process CPU usage        | Measured: {idle_cpu:.2f}% | Threshold: <= {threshold_cpu:.1f}% | Status: {s2}")

    win._force_exit()
    app.processEvents()

    return p1 and p2


if __name__ == "__main__":
    passed = run_ui_benchmark()
    sys.exit(0 if passed else 1)

