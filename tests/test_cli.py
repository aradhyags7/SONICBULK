"""Integration tests for the headless CLI interface."""

import csv
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from aiohttp.test_utils import TestServer

from app.cli.app_cli import build_parser, run_cli
from app.sources.mock_provider import MockProvider
from tests.test_server import MockAudioServer

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
async def audio_server() -> AsyncGenerator[TestServer, None]:
    server_impl = MockAudioServer()
    server = TestServer(server_impl.app)
    await server.start_server()
    yield server
    await server.close()


@pytest.mark.asyncio
async def test_cli_dry_run() -> None:
    parser = build_parser()
    args = parser.parse_args(["run", str(FIXTURES_DIR / "messy_songs.txt"), "--dry-run"])
    code = await run_cli(args)
    assert code == 0


@pytest.mark.asyncio
async def test_cli_run_end_to_end_with_report(audio_server: TestServer, tmp_path: Path) -> None:
    stream_url = str(audio_server.make_url("/songs/song-001"))
    mock_prov = MockProvider(base_stream_url=stream_url)

    out_dir = tmp_path / "cli_music"
    report_file = tmp_path / "report.csv"
    db_file = tmp_path / "cli_test.db"

    parser = build_parser()
    args = parser.parse_args([
        "run",
        str(FIXTURES_DIR / "songs.csv"),
        "--out", str(out_dir),
        "--workers", "4",
        "--report", str(report_file),
        "--db", str(db_file),
    ])

    code = await run_cli(args, custom_provider=mock_prov)
    assert code == 0

    # Verify downloaded files
    mp3_files = list(out_dir.glob("*.mp3"))
    assert len(mp3_files) >= 5

    # Verify report CSV
    assert report_file.is_file()
    with open(report_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
        # Header + 5 songs
        assert len(rows) == 6
        assert rows[0] == ["Title", "Artist", "Status", "Confidence", "Score", "Path", "Error"]
