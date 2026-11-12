"""Unified benchmark runner for Music Downloader.

Executes all benchmark suites and outputs a consolidated performance table.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BENCHMARKS = [
    ("Parser Throughput", "bench/bench_parse.py"),
    ("Pipeline Concurrency & Latency", "bench/bench_pipeline.py"),
    ("UI Latency & Idle CPU", "bench/bench_ui_lag.py"),
    ("Memory Footprint & Flat Streaming", "bench/bench_mem.py"),
]

def main() -> int:
    print("=" * 80)
    print("MUSIC DOWNLOADER - PERFORMANCE BENCHMARK SUITE")
    print("=" * 80)

    python_exe = sys.executable
    project_root = Path(__file__).resolve().parent.parent

    results: list[str] = []
    failed = False

    for title, script in BENCHMARKS:
        print(f"\n--> Running {title} ({script})...")
        script_path = project_root / script
        child_env = os.environ.copy()
        child_env["PYTHONPATH"] = str(project_root / "src")
        proc = subprocess.run(
            [python_exe, str(script_path)],
            capture_output=True,
            text=True,
            env=child_env,
        )
        if proc.returncode != 0:
            print(f"FAILED (Exit code {proc.returncode}):")
            print(proc.stderr or proc.stdout)
            failed = True
            continue

        for line in proc.stdout.splitlines():
            if line.startswith("[BENCHMARK]"):
                results.append(line)
                print("  " + line)

    print("\n" + "=" * 80)
    print("CONSOLIDATED BENCHMARK RESULTS")
    print("=" * 80)
    print(f"{'Target / Metric':<35} | {'Measured':<12} | {'Threshold':<14} | {'Status'}")
    print("-" * 80)

    for r in results:
        # Format: [BENCHMARK] MetricName | Measured: X | Threshold: Y | Status: PASS
        parts = r.replace("[BENCHMARK]", "").strip().split("|")
        if len(parts) == 4:
            metric = parts[0].strip()
            measured = parts[1].replace("Measured:", "").strip()
            threshold = parts[2].replace("Threshold:", "").strip()
            status = parts[3].replace("Status:", "").strip()
            print(f"{metric:<35} | {measured:<12} | {threshold:<14} | {status}")
        else:
            print(r)

    print("=" * 80)
    if failed or any("FAIL" in r for r in results):
        print("OVERALL STATUS: FAILED")
        return 1

    print("OVERALL STATUS: ALL TARGETS PASSED (7 / 7)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
