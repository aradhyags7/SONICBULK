"""Tests for real audio providers and yt-dlp worker pool crash recovery."""

import pytest

from app.sources.direct import DirectURLProvider
from app.sources.internet_archive import InternetArchiveProvider
from app.sources.jamendo import JamendoProvider
from app.sources.ytdlp_pool import YtDlpWorkerPool
from app.sources.ytdlp_provider import YtDlpProvider


@pytest.mark.asyncio
async def test_direct_url_provider() -> None:
    provider = DirectURLProvider()
    candidates = await provider.search("https://example.com/audio/song.mp3")
    assert len(candidates) == 1
    assert candidates[0].title == "song"
    assert candidates[0].url == "https://example.com/audio/song.mp3"

    stream = await provider.resolve(candidates[0])
    assert stream.url == "https://example.com/audio/song.mp3"
    assert stream.format == "mp3"


@pytest.mark.asyncio
async def test_ytdlp_pool_lifecycle_and_crash_isolation() -> None:
    pool = YtDlpWorkerPool(pool_size=1)
    await pool.start()

    try:
        # 1. Ping / search request works
        payload = {"action": "search", "query": "test", "limit": 1}
        resp = await pool.execute(payload)
        assert resp.get("status") == "ok"

        # 2. Simulate unexpected crash on worker
        worker = await pool._queue.get()
        worker.proc.kill()
        await worker.proc.wait()
        await pool._queue.put(worker)

        # 3. Executing against the dead worker fails for that specific job and triggers automatic respawn
        try:
            await pool.execute(payload)
        except RuntimeError:
            pass

        # 4. Subsequent job succeeds on the respawned worker
        resp2 = await pool.execute(payload)
        assert resp2.get("status") == "ok"
        assert len(pool._all_workers) == 1
    finally:
        await pool.close()


@pytest.mark.asyncio
async def test_ytdlp_provider_disabled_by_default() -> None:
    provider = YtDlpProvider(enabled=False)
    assert not provider.is_enabled
    # Disabled provider should return empty candidates immediately
    results = await provider.search("Queen - Bohemian Rhapsody")
    assert results == []


@pytest.mark.asyncio
async def test_jamendo_provider_search_structure() -> None:
    provider = JamendoProvider()
    assert provider.name == "jamendo"
    assert provider.is_enabled


@pytest.mark.asyncio
async def test_internet_archive_provider_search_structure() -> None:
    provider = InternetArchiveProvider()
    assert provider.name == "archive"
    assert provider.is_enabled
