"""Unit and integration tests for the streaming download engine."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path

import aiohttp
import pytest
from aiohttp.test_utils import TestServer

from app.core.models import DownloadJob, SongEntry, StreamInfo
from app.pipeline.adaptive import AdaptiveConcurrencyController, calculate_backoff
from app.pipeline.download_stage import (
    CHUNK_SIZE,
    DownloadEngine,
)
from app.utils.rate_limiter import TokenBucketRateLimiter
from tests.test_server import SONG_DATA, SONG_ETAG, MockAudioServer


@pytest.fixture
async def audio_server() -> AsyncGenerator[TestServer, None]:
    server_impl = MockAudioServer()
    server = TestServer(server_impl.app)
    await server.start_server()
    yield server
    await server.close()


@pytest.fixture
async def client_session() -> AsyncGenerator[aiohttp.ClientSession, None]:
    session = aiohttp.ClientSession()
    yield session
    await session.close()


def make_job(url: str, etag: str | None = SONG_ETAG, size: int = len(SONG_DATA)) -> tuple[DownloadJob, StreamInfo]:
    song = SongEntry(raw_text="Test - Track", artist="Test", title="Track")
    job = DownloadJob(song=song, batch_id="b-test")
    stream = StreamInfo(url=url, etag=etag, size_bytes=size, format="mp3")
    return job, stream


@pytest.mark.asyncio
async def test_clean_download(audio_server: TestServer, client_session: aiohttp.ClientSession, tmp_path: Path) -> None:
    engine = DownloadEngine(client_session)
    dest = tmp_path / "song.mp3"
    url = f"{audio_server.make_url('/songs/song-001')}"
    job, stream = make_job(url)

    progress_updates: list[int] = []
    def on_prog(bytes_down: int, total: int | None, speed: float) -> None:
        progress_updates.append(bytes_down)

    out_path = await engine.download_file(job, stream, dest, on_progress=on_prog)
    assert out_path.is_file()
    assert out_path.read_bytes() == SONG_DATA
    assert not dest.with_name("song.mp3.part").exists()
    assert len(progress_updates) > 0


@pytest.mark.asyncio
async def test_resume_at_random_offset(audio_server: TestServer, client_session: aiohttp.ClientSession, tmp_path: Path) -> None:
    # Pre-populate .part file with first 75,000 bytes
    dest = tmp_path / "song_resume.mp3"
    part_path = dest.with_name("song_resume.mp3.part")
    offset = 75000
    part_path.write_bytes(SONG_DATA[:offset])

    engine = DownloadEngine(client_session)
    url = f"{audio_server.make_url('/songs/song-002')}"
    job, stream = make_job(url)

    out_path = await engine.download_file(job, stream, dest)
    assert out_path.is_file()
    assert out_path.read_bytes() == SONG_DATA


@pytest.mark.asyncio
async def test_if_range_mismatch_restarts_from_zero(
    audio_server: TestServer, client_session: aiohttp.ClientSession, tmp_path: Path
) -> None:
    # Partial file exists, but ETag is mismatched
    dest = tmp_path / "song_mismatch.mp3"
    part_path = dest.with_name("song_mismatch.mp3.part")
    part_path.write_bytes(b"CORRUPT_OLD_DATA" * 100)

    engine = DownloadEngine(client_session)
    url = f"{audio_server.make_url('/songs/song-003')}"
    job, stream = make_job(url, etag='"mismatched-etag"')

    out_path = await engine.download_file(job, stream, dest)
    assert out_path.is_file()
    assert out_path.read_bytes() == SONG_DATA


@pytest.mark.asyncio
async def test_http_416_handling(audio_server: TestServer, client_session: aiohttp.ClientSession, tmp_path: Path) -> None:
    # .part file already has the full size (256 KiB)
    dest = tmp_path / "song_416.mp3"
    part_path = dest.with_name("song_416.mp3.part")
    part_path.write_bytes(SONG_DATA)

    engine = DownloadEngine(client_session)
    url = f"{audio_server.make_url('/range-416/song-004')}"
    job, stream = make_job(url)

    out_path = await engine.download_file(job, stream, dest)
    assert out_path.is_file()
    assert out_path.read_bytes() == SONG_DATA


@pytest.mark.asyncio
async def test_flaky_retry(audio_server: TestServer, client_session: aiohttp.ClientSession, tmp_path: Path) -> None:
    # Flaky endpoint fails 2 times with 503, succeeds on 3rd attempt
    engine = DownloadEngine(client_session, max_retries=5)
    dest = tmp_path / "song_flaky.mp3"
    url = f"{audio_server.make_url('/flaky/song-005')}"
    job, stream = make_job(url)

    out_path = await engine.download_file(job, stream, dest)
    assert out_path.is_file()
    assert out_path.read_bytes() == SONG_DATA


@pytest.mark.asyncio
async def test_rate_limit_retry_and_adaptive_concurrency(
    audio_server: TestServer, client_session: aiohttp.ClientSession, tmp_path: Path
) -> None:
    adaptive = AdaptiveConcurrencyController(initial_concurrency=4)
    engine = DownloadEngine(client_session, adaptive_controller=adaptive, max_retries=4)
    dest = tmp_path / "song_ratelimit.mp3"
    url = f"{audio_server.make_url('/rate-limit/song-006')}"
    job, stream = make_job(url)

    out_path = await engine.download_file(job, stream, dest)
    assert out_path.is_file()
    assert out_path.read_bytes() == SONG_DATA
    # Concurrency was reduced on 429
    assert adaptive.concurrency <= 4


@pytest.mark.asyncio
async def test_cancel_safety(audio_server: TestServer, client_session: aiohttp.ClientSession, tmp_path: Path) -> None:
    engine = DownloadEngine(client_session)
    dest = tmp_path / "song_cancel.mp3"
    url = f"{audio_server.make_url('/songs/song-007')}"
    job, stream = make_job(url)

    cancel_event = asyncio.Event()

    def on_prog(bytes_down: int, total: int | None, speed: float) -> None:
        if bytes_down >= CHUNK_SIZE:
            cancel_event.set()

    with pytest.raises(asyncio.CancelledError):
        await engine.download_file(job, stream, dest, on_progress=on_prog, cancel_event=cancel_event)

    # Destination file should NOT exist (never corrupted)
    assert not dest.exists()
    # .part file should remain for future resume
    assert dest.with_name("song_cancel.mp3.part").exists()


@pytest.mark.asyncio
async def test_bandwidth_rate_limiter() -> None:
    # Limit to 50 KiB/s
    limiter = TokenBucketRateLimiter(rate_bps=50 * 1024)
    start = asyncio.get_event_loop().time()
    # Acquire 100 KiB (should take roughly ~1.0 s)
    await limiter.acquire(50 * 1024)
    await limiter.acquire(50 * 1024)
    elapsed = asyncio.get_event_loop().time() - start
    assert elapsed >= 0.8


def test_backoff_bounds() -> None:
    # Verify exponential backoff and jitter bounds
    for attempt in range(1, 6):
        delay = calculate_backoff(attempt, base=1.0, cap=30.0)
        assert 0.0 <= delay <= min(30.0, 1.0 * (2 ** attempt))

    # Retry-After header honored
    assert calculate_backoff(1, retry_after=5.5) == 5.5
