"""Benchmark: Parse 1,000 messy playlist lines in < 1.0 s."""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app.parse.unified import parse_text_input

SAMPLE_LINES = [
    "1. Queen - Bohemian Rhapsody (Official Video) [HD] 05:55",
    "#2) The Beatles - Hey Jude (Remastered 2015) 120 bpm",
    '3. "Imagine" by John Lennon https://youtube.com/watch?v=123',
    "• Michael Jackson - Billie Jean [Audio] 117 BPM",
    "▫ AC/DC: Back in Black (Official Music Video)",
    "6. Drake feat. Rihanna - Take Care (Visualizer) 4:37",
    "7. Ed Sheeran - Shape of You [Lyrics Video] 🔥🎵",
    "8 - Adele - Rolling in the Deep (Live at the Royal Albert Hall)",
    "9. Pink Floyd - Comfortably Numb",
    "10. Hotel California by Eagles",
]


def run_benchmark() -> bool:
    # Build 1,000 distinct lines
    lines = []
    for i in range(100):
        for line in SAMPLE_LINES:
            lines.append(f"{i * 10}. {line}")

    content = "\n".join(lines)
    assert len(lines) == 1000

    start = time.perf_counter()
    doc = parse_text_input(content)
    elapsed = time.perf_counter() - start

    assert len(doc.songs) == 1000
    threshold = 1.0
    passed = elapsed < threshold

    status_str = "PASS" if passed else "FAIL"
    print(f"[BENCHMARK] Parse 1,000 lines | Measured: {elapsed:.3f} s | Threshold: < {threshold:.1f} s | Status: {status_str}")
    return passed


if __name__ == "__main__":
    passed = run_benchmark()
    sys.exit(0 if passed else 1)

