"""Tests for mutagen tagging, path sanitization, folder layout, and skip-existing rerun."""

import time
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from aiohttp.test_utils import TestServer
from mutagen.id3 import ID3

from app.core.config import AppSettings
from app.core.models import SongEntry
from app.core.sleep_blocker import SleepBlocker
from app.db.repository import DatabaseRepository
from app.pipeline.convert import convert_audio_file
from app.pipeline.engine import PipelineEngine
from app.pipeline.tag_stage import tag_audio_file
from app.sources.mock_provider import MockProvider
from app.utils.paths import generate_output_path, resolve_collision_path, sanitize_filename
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
    repository = DatabaseRepository(tmp_path / "tag_test.db")
    await repository.initialize()
    yield repository
    await repository.close()


class TestPathSanitizationAndLayout:
    def test_illegal_characters_sanitized(self) -> None:
        raw = 'Queen / David Bowie: "Under Pressure"? *1981* <Remaster> | #1'
        clean = sanitize_filename(raw)
        assert "/" not in clean
        assert ":" not in clean
        assert '"' not in clean
        assert "?" not in clean
        assert "*" not in clean
        assert "<" not in clean
        assert ">" not in clean
        assert "|" not in clean

    def test_windows_reserved_names(self) -> None:
        assert sanitize_filename("CON") == "_CON"
        assert sanitize_filename("aux.mp3") == "_aux.mp3"
        assert sanitize_filename("nul") == "_nul"

    def test_max_path_length_truncation(self, tmp_path: Path) -> None:
        very_long_title = "A" * 300
        path = generate_output_path(
            output_dir=tmp_path,
            layout="flat",
            template="{artist} - {title}",
            artist="Queen",
            title=very_long_title,
            extension="mp3",
        )
        assert len(str(path)) <= 250
        assert path.suffix == ".mp3"

    def test_folder_layout_flat_vs_artist_album(self, tmp_path: Path) -> None:
        flat_p = generate_output_path(
            output_dir=tmp_path,
            layout="flat",
            template="{artist} - {title}",
            artist="Queen",
            title="Bohemian Rhapsody",
            album="A Night at the Opera",
        )
        assert flat_p.parent == tmp_path

        nested_p = generate_output_path(
            output_dir=tmp_path,
            layout="artist_album",
            template="{title}",
            artist="Queen",
            title="Bohemian Rhapsody",
            album="A Night at the Opera",
        )
        assert nested_p.parent == tmp_path / "Queen" / "A Night at the Opera"

    def test_collision_suffix(self, tmp_path: Path) -> None:
        base_file = tmp_path / "song.mp3"
        base_file.write_text("audio")

        coll1 = resolve_collision_path(base_file)
        assert coll1.name == "song (1).mp3"

        coll1.write_text("audio 2")
        coll2 = resolve_collision_path(base_file)
        assert coll2.name == "song (2).mp3"


class TestMutagenTagging:
    def test_mp3_tagging(self, tmp_path: Path) -> None:
        # Create minimal valid MP3 frame
        mp3_file = tmp_path / "sample.mp3"
        # Minimum MP3 frame sync bytes
        mp3_file.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 400)

        ok = tag_audio_file(
            mp3_file,
            title="Bohemian Rhapsody",
            artist="Queen",
            album="A Night at the Opera",
        )
        assert ok
        tags = ID3(str(mp3_file))
        assert tags.get("TIT2").text[0] == "Bohemian Rhapsody"
        assert tags.get("TPE1").text[0] == "Queen"
        assert tags.get("TALB").text[0] == "A Night at the Opera"


class TestSleepBlocker:
    def test_sleep_blocker_toggle(self) -> None:
        blocker = SleepBlocker()
        blocker.enable()
        assert blocker.is_blocking
        blocker.disable()
        assert not blocker.is_blocking


class TestConversion:
    def test_native_conversion_passthrough(self, tmp_path: Path) -> None:
        p = tmp_path / "sample.mp3"
        p.write_text("audio data")
        res = convert_audio_file(p, target_format="native")
        assert res == p


@pytest.mark.asyncio
async def test_rerun_completed_batch_skips_in_under_5_seconds(
    audio_server: TestServer, repo: DatabaseRepository, tmp_path: Path
) -> None:
    # Requirement: "Rerun of a completed batch: all skipped in <5 s."
    songs = [
        SongEntry(raw_text=f"Artist {i} - Song {i}", artist=f"Artist {i}", title=f"Song {i}")
        for i in range(25)
    ]
    batch_1 = "batch-first-run"
    jobs_1 = await repo.create_batch(batch_1, songs)

    stream_url = str(audio_server.make_url("/songs/song-001"))
    provider = MockProvider(base_stream_url=stream_url)
    settings = AppSettings(
        output_dir=str(tmp_path / "skip_music"),
        download_concurrency=8,
    )
    engine = PipelineEngine(settings=settings, repository=repo, provider=provider)
    await engine.initialize()

    try:
        # Run 1: Download all
        summary_1 = await engine.run_batch(batch_1, jobs_1)
        assert summary_1.downloaded == 25

        # Run 2: Re-run with another batch ID but same songs
        batch_2 = "batch-second-run"
        jobs_2 = await repo.create_batch(batch_2, songs)

        start = time.perf_counter()
        summary_2 = await engine.run_batch(batch_2, jobs_2)
        elapsed = time.perf_counter() - start

        # Must skip all songs
        assert summary_2.skipped == 25
        assert summary_2.downloaded == 0
        assert elapsed < 5.0, f"Rerun took {elapsed:.2f}s (target < 5.0s)"
    finally:
        await engine.close()
