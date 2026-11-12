"""Unit tests for SQLite WAL database repository."""

from pathlib import Path

import pytest

from app.core.models import Candidate, Confidence, JobStatus, MatchDecision, SongEntry, StreamInfo
from app.db.repository import DatabaseRepository


@pytest.fixture
async def repo(tmp_path: Path) -> DatabaseRepository:
    db_file = tmp_path / "test_jobs.db"
    repository = DatabaseRepository(db_file)
    await repository.initialize()
    yield repository
    await repository.close()


@pytest.mark.asyncio
async def test_wal_mode_enabled(repo: DatabaseRepository) -> None:
    # Verify WAL journal mode is set
    async with repo._ensure_conn().execute("PRAGMA journal_mode") as cursor:
        row = await cursor.fetchone()
        assert row is not None
        assert row[0].lower() == "wal"


@pytest.mark.asyncio
async def test_create_batch_and_query_jobs(repo: DatabaseRepository) -> None:
    songs = [
        SongEntry(raw_text="Queen - Bohemian Rhapsody", artist="Queen", title="Bohemian Rhapsody"),
        SongEntry(raw_text="The Beatles - Let It Be", artist="The Beatles", title="Let It Be"),
    ]
    jobs = await repo.create_batch("batch-1", songs)
    assert len(jobs) == 2
    assert jobs[0].status == JobStatus.QUEUED

    retrieved = await repo.get_jobs_for_batch("batch-1")
    assert len(retrieved) == 2
    assert retrieved[0].song.title == "Bohemian Rhapsody"
    assert retrieved[1].song.title == "Let It Be"


@pytest.mark.asyncio
async def test_update_status_and_progress(repo: DatabaseRepository) -> None:
    songs = [SongEntry(raw_text="Queen - Bohemian Rhapsody", artist="Queen", title="Bohemian Rhapsody")]
    jobs = await repo.create_batch("batch-1", songs)
    job_id = jobs[0].id

    await repo.update_job_status(job_id, JobStatus.DOWNLOADING)
    await repo.update_job_progress(job_id, bytes_downloaded=1024, total_bytes=4096, speed_bps=500.0)

    job = await repo.get_job(job_id)
    assert job is not None
    assert job.status == JobStatus.DOWNLOADING
    assert job.bytes_downloaded == 1024
    assert job.total_bytes == 4096
    assert job.speed_bps == 500.0


@pytest.mark.asyncio
async def test_match_decision_and_candidate_persistence(repo: DatabaseRepository) -> None:
    songs = [SongEntry(raw_text="Queen - Bohemian Rhapsody", artist="Queen", title="Bohemian Rhapsody")]
    jobs = await repo.create_batch("batch-1", songs)
    job_id = jobs[0].id

    cand = Candidate(
        provider="archive",
        source_id="item-123",
        title="Bohemian Rhapsody",
        artist="Queen",
        album="A Night at the Opera",
        duration_seconds=355.0,
        url="https://archive.org/download/item/song.mp3",
        is_official=True,
        score=0.95,
    )
    decision = MatchDecision(
        candidate=cand,
        confidence=Confidence.HIGH,
        score=0.95,
        title_similarity=0.98,
        artist_similarity=0.92,
        penalty_applied=0.0,
        reason="Exact title and artist match",
    )
    stream = StreamInfo(
        url="https://archive.org/download/item/song.mp3",
        size_bytes=8192000,
        mime_type="audio/mpeg",
        etag='"etag123"',
    )

    await repo.save_match_decision(job_id, decision, stream)
    await repo.save_candidates(job_id, [cand])

    cands = await repo.get_candidates(job_id)
    assert len(cands) == 1
    assert cands[0].source_id == "item-123"

    job = await repo.get_job(job_id)
    assert job is not None
    assert job.match_decision is not None
    assert job.match_decision.confidence == Confidence.HIGH
    assert job.stream_info is not None
    assert job.stream_info.etag == '"etag123"'


@pytest.mark.asyncio
async def test_cache_ttl_and_pruning(repo: DatabaseRepository) -> None:
    await repo.set_cache("key-valid", "search", {"results": [1, 2]}, ttl_seconds=3600)
    await repo.set_cache("key-expired", "search", {"results": [3]}, ttl_seconds=-10)

    val_valid = await repo.get_cache("key-valid")
    assert val_valid == {"results": [1, 2]}

    val_expired = await repo.get_cache("key-expired")
    assert val_expired is None

    deleted = await repo.prune_expired_cache()
    assert deleted >= 1


@pytest.mark.asyncio
async def test_unfinished_jobs_recovery(repo: DatabaseRepository) -> None:
    songs = [
        SongEntry(raw_text="Queen - Bohemian Rhapsody", artist="Queen", title="Bohemian Rhapsody"),
        SongEntry(raw_text="The Beatles - Let It Be", artist="The Beatles", title="Let It Be"),
    ]
    jobs = await repo.create_batch("batch-rec", songs)
    # Complete job 0, leave job 1 downloading
    await repo.update_job_status(jobs[0].id, JobStatus.DONE, output_path="/music/queen.mp3")
    await repo.update_job_status(jobs[1].id, JobStatus.DOWNLOADING)

    unfinished = await repo.get_unfinished_jobs()
    assert len(unfinished) == 1
    assert unfinished[0].id == jobs[1].id
