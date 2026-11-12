"""Benchmark: Memory RSS with 2,000-song batch (< 200 MB) and 500 MB stream delta (< 50 MB)."""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

import aiohttp
import psutil
from aiohttp import web
from aiohttp.test_utils import TestServer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app.core.config import AppSettings
from app.core.models import DownloadJob, SongEntry, StreamInfo
from app.db.repository import DatabaseRepository
from app.pipeline.download_stage import DownloadEngine
from app.pipeline.engine import PipelineEngine
from app.sources.mock_provider import MockProvider


async def large_stream_handler(request: web.Request) -> web.StreamResponse:
    """Stream 500 MB of data in 64 KiB chunks without keeping 500 MB in RAM."""
    chunk = bytes([(i % 256) for i in range(64 * 1024)])
    total_size = 500 * 1024 * 1024  # 500 MB
    num_chunks = total_size // len(chunk)

    resp = web.StreamResponse(
        status=200,
        headers={
            "Content-Type": "audio/mpeg",
            "Content-Length": str(total_size),
        },
    )
    await resp.prepare(request)
    for _ in range(num_chunks):
        await resp.write(chunk)
    return resp


async def run_memory_benchmarks() -> bool:
    proc = psutil.Process(os.getpid())
    all_passed = True
    tmp_dir = Path(tempfile.mkdtemp(prefix="bench_mem_"))

    try:
        # Benchmark 1: 2,000-song batch RSS footprint (< 200 MB)
        repo = DatabaseRepository(tmp_dir / "mem_test.db")
        await repo.initialize()

        print("[INFO] Generating 2,000 songs...")
        songs = [
            SongEntry(raw_text=f"Artist {i} - Song Title {i}", artist=f"Artist {i}", title=f"Song Title {i}")
            for i in range(2000)
        ]

        await repo.create_batch("batch-2000", songs)

        provider = MockProvider(search_latency=0.0, resolve_latency=0.0)
        settings = AppSettings(
            output_dir=str(tmp_dir / "music_2000"),
            download_concurrency=5,
            search_concurrency=8,
            resolve_concurrency=6,
        )

        engine = PipelineEngine(settings=settings, repository=repo, provider=provider)
        await engine.initialize()

        # Measure RSS with 2,000 jobs in memory & pipeline
        rss_2000_mb = proc.memory_info().rss / (1024 * 1024)
        threshold_batch_mb = 200.0
        p1 = rss_2000_mb < threshold_batch_mb
        s1 = "PASS" if p1 else "FAIL"
        print(f"[BENCHMARK] RSS with 2,000-song batch       | Measured: {rss_2000_mb:.1f} MB | Threshold: < {threshold_batch_mb:.1f} MB | Status: {s1}")
        if not p1:
            all_passed = False

        await engine.close()
        await repo.close()

        # Benchmark 2: 500 MB streaming download RSS delta (< 50 MB)
        app = web.Application()
        app.router.add_get("/stream500", large_stream_handler)
        server = TestServer(app)
        await server.start_server()

        async with aiohttp.ClientSession() as session:
            engine_down = DownloadEngine(session=session)
            dest = tmp_dir / "large_500mb.mp3"
            stream_info = StreamInfo(
                url=str(server.make_url("/stream500")),
                size_bytes=500 * 1024 * 1024,
                format="mp3",
            )
            job = DownloadJob(song=SongEntry(raw_text="Large", title="Large"), batch_id="b-large")

            # Record baseline RSS before download
            rss_before_mb = proc.memory_info().rss / (1024 * 1024)

            # Stream download
            await engine_down.download_file(job, stream_info, dest)

            # Record RSS after 500 MB streamed
            rss_after_mb = proc.memory_info().rss / (1024 * 1024)
            rss_delta_mb = max(0.0, rss_after_mb - rss_before_mb)

            threshold_stream_mb = 50.0
            p2 = rss_delta_mb < threshold_stream_mb
            s2 = "PASS" if p2 else "FAIL"
            print(f"[BENCHMARK] 500 MB stream RSS delta         | Measured: {rss_delta_mb:.1f} MB | Threshold: < {threshold_stream_mb:.1f} MB | Status: {s2}")
            if not p2:
                all_passed = False

            # Verify downloaded file size is exactly 500 MB
            assert dest.stat().st_size == 500 * 1024 * 1024

        await server.close()

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return all_passed


if __name__ == "__main__":
    passed = asyncio.run(run_memory_benchmarks())
    sys.exit(0 if passed else 1)
