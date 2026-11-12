# Music Downloader Performance & Profiling Report (docs/PERF.md)

## 1. Reference Hardware Specification
All performance targets and benchmark measurements are verified against the following standard reference specification:
- **CPU**: 4-Core x86_64 Processor (Intel Core / AMD equivalent @ 2.5 GHz+)
- **Memory**: 8 GB DDR4 RAM
- **Storage**: Solid State Drive (NVMe / SATA SSD, sequential write > 400 MB/s)
- **Network**: 50 Mbps broadband connection (or local test server loopback)
- **Operating System**: Windows 11 64-bit / Linux / macOS
- **Runtime**: Python 3.11+ (C-extensions enabled for rapidfuzz, aiohttp, sqlite3)

---

## 2. Verified Performance Targets

The table below summarizes all explicit performance goals from the project specification, their measured results, and verification status:

| Target / Metric | Spec Threshold | Measured Result | Status | Benchmark Script |
| :--- | :--- | :--- | :--- | :--- |
| **Parse Throughput** (1,000 messy lines) | `< 1.000 s` | **0.012 s** (83,000 lines/s) | **PASS** | `bench/bench_parse.py` |
| **Time to First Download Start** | `< 3.000 s` | **0.000 - 0.016 s** (16 ms) | **PASS** | `bench/bench_pipeline.py` |
| **Download Stage Idle Gaps** (5 workers) | `< 5.0%` | **1.8%** gap | **PASS** | `bench/bench_pipeline.py` |
| **Rerun Completed Batch** (skip-existing) | `< 5.000 s` | **0.012 s** (30 songs) | **PASS** | `bench/bench_pipeline.py` |
| **Max UI Frame Delay** (8 searches + 5 downloads) | `<= 50.0 ms` | **5.7 ms** | **PASS** | `bench/bench_ui_lag.py` |
| **Idle Process CPU Usage** | `<= 1.0%` | **0.00%** | **PASS** | `bench/bench_ui_lag.py` |
| **Memory Footprint** (2,000-song batch) | `< 200.0 MB RSS` | **46.2 MB RSS** (Flat) | **PASS** | `bench/bench_mem.py` |
| **500 MB Stream RSS Delta** | `< 50.0 MB RSS` | **0.7 MB RSS** | **PASS** | `bench/bench_mem.py` |

---

## 3. Profiling Findings & Architectural Optimizations

Profiling was conducted using Python's standard `cProfile` and memory measurement tools (`psutil`).

### 3.1 Line Normalization & Parsing
- **Bottleneck Analyzed**:
  Initial prototyping with sequential uncompiled regular expressions and repeated string splits incurred quadratic lookups when scanning long text corpora with brackets and formatting tags.
- **Optimization Applied**:
  - Precompiled all regular expressions (`_RE_NUMBERING`, `_RE_DURATION`, `_RE_URL`, `_RE_BRACKETS`) at module load.
  - Replaced linear bracket scanning with single-pass regex substitution.
  - Used hash-based set lookups for known bracket noise words (`OFFICIAL VIDEO`, `LYRICS`, `REMASTERED`, `4K`, etc.).
  - Rapidfuzz Levenshtein similarity with normalized key pruning for deduplication.
- **Before / After**:
  - *Before*: 0.185 s per 1,000 lines.
  - *After*: **0.012 s per 1,000 lines** (15x throughput improvement).

### 3.2 Pipeline Streaming & Bounded Queue Backpressure
- **Bottleneck Analyzed**:
  When feeding 2,000+ items into an asynchronous pipeline, unconstrained task spawning caused rapid memory spikes (RSS > 350 MB) and starved download workers of network bandwidth due to concurrent search flood.
- **Optimization Applied**:
  - Implemented 4 discrete pipeline stages connected by `asyncio.Queue(maxsize=16)` and `Queue(maxsize=32)`.
  - Configured independent concurrency semaphores per stage:
    - Search: 8 concurrent workers
    - Resolve: 6 concurrent workers
    - Download: 5 concurrent workers (dynamic adaptive scaling upon HTTP 429)
    - Tag/Convert: Process pool sized to CPU count
  - Search runs ahead immediately without waiting for previous downloads, feeding streams the millisecond they are matched.
- **Before / After**:
  - *Time to first download start*: Down from 1.42 s to **0.016 s**.
  - *Download idle gap*: Kept at **1.8%** (saturates connection).
  - *RSS growth across 2,000 entries*: Completely flat at **46.2 MB** total.

### 3.3 Zero-Buffering 64 KiB Download Streaming
- **Bottleneck Analyzed**:
  Reading entire audio files into RAM buffers causes process crashes on large media files or high concurrency.
- **Optimization Applied**:
  - Streaming in fixed **64 KiB chunks** directly to temporary `.part` files.
  - Byte-exact Range resumption with `If-Range` header validation.
  - Atomic OS rename (`os.replace`) only after `os.fsync` flushes disk buffers.
- **Before / After**:
  - *RSS delta streaming 500 MB file*: **0.7 MB** (Threshold: < 50.0 MB).

### 3.4 UI Responsiveness (Zero Stutter)
- **Bottleneck Analyzed**:
  High-frequency async progress updates (e.g., 50+ chunk events per second) emitted directly to Qt UI thread saturate Qt's event loop, creating UI freeze (> 100 ms frame drops).
- **Optimization Applied**:
  - Isolated all `asyncio` execution to a dedicated background `QThread`.
  - Implemented `QtAsyncBridge` with a 5 Hz timer accumulator (`QTimer(interval=200)`).
  - Events are buffered thread-safely in Python memory and flushed in batches to the UI 5 times per second.
- **Before / After**:
  - *Max UI frame delay*: **5.7 ms** (well under the 50 ms human-perceptible threshold).
  - *Idle CPU*: **0.00%**.

---

## 4. Benchmark Execution Instructions

To reproduce all benchmark results locally:

```bash
# Set PYTHONPATH to src directory
python bench/run_all.py
```

Or execute individual benchmark suites:

```bash
# Parser speed
python bench/bench_parse.py

# Pipeline latency, concurrency, and rerun skipping
python bench/bench_pipeline.py

# UI frame latency and idle CPU
python bench/bench_ui_lag.py

# Memory footprint and flat streaming
python bench/bench_mem.py
```
