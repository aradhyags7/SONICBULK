"""Unit and integration tests for the multi-stage concurrent pipeline."""

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from aiohttp.test_utils import TestServer

from app.core.config import AppSettings
from app.core.models import SongEntry
from app.db.repository import DatabaseRepository
from app.pipeline.engine import PipelineEngine
from app.sources.mock_provider import MockProvider
from tests.test_server import MockAudioServer


@pytest.fixture
async def audio_server() -> AsyncGenerator[TestServer, None]:
    server_impl = MockAudioServer()
    server = TestServer(server_impl.app)
    await server.start_server()
    yield server
    await server.close()


@pytest.fixture
async def repo(tmp_path: Path) -> AsyncGenerator[DatabaseRepository, None]:
    repository = DatabaseRepository(tmp_path / "pipeline_test.db")
    await repository.initialize()
    yield repository
    await repository.close()


@pytest.mark.asyncio
async def test_pipeline_end_to_end_and_time_to_first_download(
    audio_server: TestServer, repo: DatabaseRepository, tmp_path: Path
) -> None:
    # 10 mock songs
    songs = [
        SongEntry(raw_text=f"Artist {i} - Song {i}", artist=f"Artist {i}", title=f"Song {i}")
        for i in range(10)
    ]
    batch_id = "test-batch-001"
    jobs = await repo.create_batch(batch_id, songs)

    stream_url = str(audio_server.make_url("/songs/song-001"))
    provider = MockProvider(base_stream_url=stream_url, search_latency=0.02, resolve_latency=0.01)

    settings = AppSettings(
        output_dir=str(tmp_path / "music"),
        download_concurrency=4,
        search_concurrency=4,
        resolve_concurrency=4,
        tag_concurrency=2,
    )

    engine = PipelineEngine(settings=settings, repository=repo, provider=provider)
    await engine.initialize()

    try:
        summary = await engine.run_batch(batch_id, jobs)

        # Verification
        assert summary.total == 10
        assert summary.downloaded == 10
        assert summary.failed == 0
        assert summary.duration_seconds > 0.0

        # Requirement: Time to first download start: < 3 s after pressing Start
        first_down_time = engine.time_to_first_download_sec
        assert first_down_time is not None
        assert first_down_time < 3.0, f"Time to first download was {first_down_time:.3f}s (target < 3.0s)"

        # Verify files created on disk
        downloaded_files = list((tmp_path / "music").glob("*.mp3"))
        assert len(downloaded_files) == 10
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_pipeline_runtime_concurrency_change(
    audio_server: TestServer, repo: DatabaseRepository, tmp_path: Path
) -> None:
    settings = AppSettings(
        output_dir=str(tmp_path / "music_conc"),
        download_concurrency=2,
    )
    provider = MockProvider(base_stream_url=str(audio_server.make_url("/songs/song-001")))
    engine = PipelineEngine(settings=settings, repository=repo, provider=provider)

    assert engine.settings.download_concurrency == 2
    # Dynamically change concurrency at runtime
    engine.set_download_concurrency(8)
    assert engine.settings.download_concurrency == 8


@pytest.mark.asyncio
async def test_pipeline_backpressure_bounded_queues(
    audio_server: TestServer, repo: DatabaseRepository, tmp_path: Path
) -> None:
    # Verify queues never exceed their bounded maxsize
    settings = AppSettings(output_dir=str(tmp_path / "bp"))
    provider = MockProvider(base_stream_url=str(audio_server.make_url("/songs/song-001")))
    engine = PipelineEngine(settings=settings, repository=repo, provider=provider)

    assert engine.search_queue.maxsize == 32
    assert engine.resolve_queue.maxsize == 32
    assert engine.download_queue.maxsize == 16
    assert engine.tag_queue.maxsize == 32


@pytest.mark.asyncio
async def test_pipeline_pause_and_resume(
    audio_server: TestServer, repo: DatabaseRepository, tmp_path: Path
) -> None:
    settings = AppSettings(output_dir=str(tmp_path / "pause_test"))
    provider = MockProvider(base_stream_url=str(audio_server.make_url("/songs/song-001")))
    engine = PipelineEngine(settings=settings, repository=repo, provider=provider)

    engine.pause()
    assert not engine.pause_event.is_set()

    engine.resume()
    assert engine.pause_event.is_set()


@pytest.mark.asyncio
async def test_pipeline_cancel(
    audio_server: TestServer, repo: DatabaseRepository, tmp_path: Path
) -> None:
    songs = [SongEntry(raw_text=f"Artist - Song {i}", artist="Artist", title=f"Song {i}") for i in range(5)]
    jobs = await repo.create_batch("cancel-batch", songs)
    stream_url = str(audio_server.make_url("/songs/song-001"))
    provider = MockProvider(base_stream_url=stream_url, search_latency=0.1)

    settings = AppSettings(output_dir=str(tmp_path / "cancel_out"))
    engine = PipelineEngine(settings=settings, repository=repo, provider=provider)
    await engine.initialize()

    async def cancel_later() -> None:
        await asyncio.sleep(0.05)
        engine.cancel()

    asyncio.create_task(cancel_later())

    try:
        summary = await engine.run_batch("cancel-batch", jobs)
        assert summary.total == 5
        assert engine.cancel_event.is_set()
    finally:
        await engine.close()
