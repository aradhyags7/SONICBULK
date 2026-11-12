"""Asynchronous SQLite repository for job state and caching with WAL mode."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any

import aiosqlite

from app.core.models import (
    Candidate,
    Confidence,
    DownloadJob,
    JobStatus,
    MatchDecision,
    SongEntry,
    StreamInfo,
)
from app.db.schema import SCHEMA_SQL

logger = logging.getLogger(__name__)


class DatabaseRepository:
    """Thread-safe and async SQLite database repository."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Create tables and indexes with WAL mode enabled."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA_SQL)
        await self._conn.commit()
        logger.info("Database initialized at %s with WAL mode", self.db_path)

    async def close(self) -> None:
        """Gracefully close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    def _ensure_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database connection is not initialized.")
        return self._conn

    async def create_batch(self, batch_id: str, songs: list[SongEntry]) -> list[DownloadJob]:
        """Insert a batch and its associated song jobs in a single transaction."""
        conn = self._ensure_conn()
        now = time.time()
        jobs: list[DownloadJob] = []

        await conn.execute(
            "INSERT INTO batches (id, created_at, updated_at, total, status) VALUES (?, ?, ?, ?, ?)",
            (batch_id, now, now, len(songs), "active"),
        )

        job_records: list[tuple[Any, ...]] = []
        for song in songs:
            job = DownloadJob(song=song, batch_id=batch_id, created_at=now, updated_at=now)
            jobs.append(job)
            job_records.append((
                job.id,
                batch_id,
                song.raw_text,
                song.title,
                song.artist,
                song.query,
                song.normalized_key,
                job.status.value,
                None,
                None,
                0,
                None,
                0.0,
                now,
                now,
            ))

        await conn.executemany(
            """INSERT INTO jobs (
                id, batch_id, raw_text, title, artist, query, normalized_key,
                status, error_message, output_path, bytes_downloaded, total_bytes,
                speed_bps, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            job_records,
        )
        await conn.commit()
        return jobs

    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        error_message: str | None = None,
        output_path: str | None = None,
    ) -> None:
        """Update job lifecycle status atomically."""
        conn = self._ensure_conn()
        now = time.time()
        await conn.execute(
            """UPDATE jobs SET
                status = ?,
                error_message = COALESCE(?, error_message),
                output_path = COALESCE(?, output_path),
                updated_at = ?
            WHERE id = ?""",
            (status.value, error_message, output_path, now, job_id),
        )
        await conn.commit()

    async def update_job_progress(
        self,
        job_id: str,
        bytes_downloaded: int,
        total_bytes: int | None,
        speed_bps: float,
    ) -> None:
        """Update download progress metrics."""
        conn = self._ensure_conn()
        now = time.time()
        await conn.execute(
            """UPDATE jobs SET
                bytes_downloaded = ?,
                total_bytes = COALESCE(?, total_bytes),
                speed_bps = ?,
                updated_at = ?
            WHERE id = ?""",
            (bytes_downloaded, total_bytes, speed_bps, now, job_id),
        )
        await conn.commit()

    async def save_match_decision(
        self,
        job_id: str,
        decision: MatchDecision,
        stream_info: StreamInfo | None = None,
    ) -> None:
        """Persist match audit decision and resolved stream info."""
        conn = self._ensure_conn()
        now = time.time()
        cand = decision.candidate
        stream_json = json.dumps(stream_info.to_dict()) if stream_info else None
        stream_url = stream_info.url if stream_info else (cand.url if cand else None)

        await conn.execute(
            """INSERT OR REPLACE INTO matches (
                job_id, provider, source_id, title, artist, album,
                score, confidence, reason, stream_url, stream_info_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job_id,
                cand.provider if cand else "none",
                cand.source_id if cand else "",
                cand.title if cand else "",
                cand.artist if cand else None,
                cand.album if cand else None,
                decision.score,
                decision.confidence.value,
                decision.reason,
                stream_url,
                stream_json,
                now,
            ),
        )
        await conn.commit()

    async def save_candidates(self, job_id: str, candidates: list[Candidate]) -> None:
        """Persist retrieved candidates for audit and manual user override."""
        conn = self._ensure_conn()
        await conn.execute("DELETE FROM candidates WHERE job_id = ?", (job_id,))
        rows = [
            (
                job_id,
                rank,
                c.provider,
                c.source_id,
                c.title,
                c.artist,
                c.album,
                c.duration_seconds,
                c.url,
                1 if c.is_official else 0,
                c.score,
                json.dumps(c.extra),
            )
            for rank, c in enumerate(candidates, 1)
        ]
        await conn.executemany(
            """INSERT INTO candidates (
                job_id, rank, provider, source_id, title, artist, album,
                duration, url, is_official, score, extra_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        await conn.commit()

    async def get_candidates(self, job_id: str) -> list[Candidate]:
        """Fetch candidates list for a job."""
        conn = self._ensure_conn()
        cursor = await conn.execute(
            "SELECT * FROM candidates WHERE job_id = ? ORDER BY rank ASC",
            (job_id,),
        )
        rows = await cursor.fetchall()
        candidates: list[Candidate] = []
        for r in rows:
            extra = json.loads(r["extra_json"]) if r["extra_json"] else {}
            candidates.append(Candidate(
                provider=r["provider"],
                source_id=r["source_id"],
                title=r["title"],
                artist=r["artist"],
                album=r["album"],
                duration_seconds=r["duration"],
                url=r["url"],
                is_official=bool(r["is_official"]),
                score=r["score"],
                extra=extra,
            ))
        return candidates

    async def get_job(self, job_id: str) -> DownloadJob | None:
        """Retrieve a job by ID with match and stream data."""
        conn = self._ensure_conn()
        cursor = await conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return await self._row_to_job(row)

    async def get_jobs_for_batch(self, batch_id: str) -> list[DownloadJob]:
        """Retrieve all jobs in a batch."""
        conn = self._ensure_conn()
        cursor = await conn.execute(
            "SELECT * FROM jobs WHERE batch_id = ? ORDER BY created_at ASC",
            (batch_id,),
        )
        rows = await cursor.fetchall()
        jobs: list[DownloadJob] = []
        for r in rows:
            job = await self._row_to_job(r)
            jobs.append(job)
        return jobs

    async def get_unfinished_jobs(self) -> list[DownloadJob]:
        """Fetch jobs from any active batch that did not reach a terminal state."""
        conn = self._ensure_conn()
        terminal = (
            JobStatus.DONE.value,
            JobStatus.SKIPPED.value,
            JobStatus.NOT_FOUND.value,
            JobStatus.FAILED.value,
        )
        placeholders = ",".join("?" for _ in terminal)
        cursor = await conn.execute(
            f"SELECT * FROM jobs WHERE status NOT IN ({placeholders}) ORDER BY created_at ASC",
            terminal,
        )
        rows = await cursor.fetchall()
        jobs: list[DownloadJob] = []
        for r in rows:
            job = await self._row_to_job(r)
            jobs.append(job)
        return jobs

    async def find_completed_by_key(self, normalized_key: str) -> str | None:
        """Find an already completed download path by song key to prevent duplicates."""
        conn = self._ensure_conn()
        cursor = await conn.execute(
            """SELECT output_path FROM jobs
            WHERE normalized_key = ? AND status = ? AND output_path IS NOT NULL
            ORDER BY updated_at DESC LIMIT 1""",
            (normalized_key, JobStatus.DONE.value),
        )
        row = await cursor.fetchone()
        if row and row["output_path"] and Path(row["output_path"]).is_file():
            return str(row["output_path"])
        return None

    async def get_cache(self, cache_key: str) -> Any | None:
        """Retrieve unexpired payload from cache."""
        conn = self._ensure_conn()
        now = time.time()
        cursor = await conn.execute(
            "SELECT payload_json FROM cache WHERE cache_key = ? AND expires_at > ?",
            (cache_key, now),
        )
        row = await cursor.fetchone()
        if row:
            try:
                return json.loads(row["payload_json"])
            except Exception:
                return None
        return None

    async def set_cache(self, cache_key: str, cache_type: str, payload: Any, ttl_seconds: float) -> None:
        """Insert or replace cache entry with expiration timestamp."""
        conn = self._ensure_conn()
        now = time.time()
        expires_at = now + ttl_seconds
        payload_json = json.dumps(payload)
        await conn.execute(
            """INSERT OR REPLACE INTO cache (cache_key, cache_type, payload_json, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)""",
            (cache_key, cache_type, payload_json, now, expires_at),
        )
        await conn.commit()

    async def prune_expired_cache(self) -> int:
        """Delete expired cache records."""
        conn = self._ensure_conn()
        now = time.time()
        cursor = await conn.execute("DELETE FROM cache WHERE expires_at <= ?", (now,))
        await conn.commit()
        return cursor.rowcount

    async def _row_to_job(self, row: sqlite3.Row) -> DownloadJob:
        song = SongEntry(
            id=row["id"],
            raw_text=row["raw_text"],
            title=row["title"],
            artist=row["artist"],
            query=row["query"],
        )
        job = DownloadJob(
            id=row["id"],
            batch_id=row["batch_id"],
            song=song,
            status=JobStatus(row["status"]),
            error_message=row["error_message"],
            output_path=row["output_path"],
            bytes_downloaded=row["bytes_downloaded"],
            total_bytes=row["total_bytes"],
            speed_bps=row["speed_bps"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

        # Check for match info
        conn = self._ensure_conn()
        cursor = await conn.execute("SELECT * FROM matches WHERE job_id = ?", (job.id,))
        m = await cursor.fetchone()
        if m:
            cand = Candidate(
                provider=m["provider"],
                source_id=m["source_id"],
                title=m["title"],
                artist=m["artist"],
                album=m["album"],
                url=m["stream_url"],
            )
            job.match_decision = MatchDecision(
                candidate=cand,
                confidence=Confidence(m["confidence"]),
                score=m["score"],
                title_similarity=m["score"],
                artist_similarity=m["score"],
                penalty_applied=0.0,
                reason=m["reason"],
            )
            if m["stream_info_json"]:
                try:
                    s_data = json.loads(m["stream_info_json"])
                    job.stream_info = StreamInfo.from_dict(s_data)
                except Exception:
                    pass

        return job
