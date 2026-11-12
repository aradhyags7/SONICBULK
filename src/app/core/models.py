"""Core domain models for Music Downloader."""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


class JobStatus(str, enum.Enum):
    """Lifecycle status of a download job."""
    QUEUED = "queued"
    SEARCHING = "searching"
    MATCHED = "matched"
    RESOLVING = "resolving"
    DOWNLOADING = "downloading"
    TAGGING = "tagging"
    DONE = "done"
    SKIPPED = "skipped"
    NOT_FOUND = "not_found"
    FAILED = "failed"


class Confidence(str, enum.Enum):
    """Match confidence tier."""
    HIGH = "high"
    LOW = "low"
    NONE = "none"


@dataclass(slots=True)
class SongEntry:
    """Represents a song item parsed from user input."""
    raw_text: str
    title: str
    artist: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    is_duplicate: bool = False
    near_duplicate_of: str | None = None
    query: str = ""

    def __post_init__(self) -> None:
        if not self.query:
            if self.artist:
                self.query = f"{self.artist} - {self.title}".strip()
            else:
                self.query = self.title.strip()

    @property
    def normalized_key(self) -> str:
        """Normalized key for exact deduplication."""
        a = (self.artist or "").strip().lower()
        t = self.title.strip().lower()
        return f"{a}:::{t}"


@dataclass(slots=True)
class Candidate:
    """Candidate song result returned from a source provider."""
    provider: str
    source_id: str
    title: str
    artist: str | None = None
    album: str | None = None
    duration_seconds: float | None = None
    url: str | None = None
    is_official: bool = False
    is_verified: bool = False
    score: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Candidate:
        return cls(**data)


@dataclass(slots=True)
class MatchDecision:
    """Audit record of a matching choice."""
    candidate: Candidate | None
    confidence: Confidence
    score: float
    title_similarity: float
    artist_similarity: float
    penalty_applied: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.candidate:
            d["candidate"] = self.candidate.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MatchDecision:
        cand_data = data.get("candidate")
        candidate = Candidate.from_dict(cand_data) if cand_data else None
        return cls(
            candidate=candidate,
            confidence=Confidence(data["confidence"]),
            score=data["score"],
            title_similarity=data["title_similarity"],
            artist_similarity=data["artist_similarity"],
            penalty_applied=data["penalty_applied"],
            reason=data["reason"],
        )


@dataclass(slots=True)
class StreamInfo:
    """Resolved audio stream information."""
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    size_bytes: int | None = None
    mime_type: str = "audio/mpeg"
    etag: str | None = None
    last_modified: str | None = None
    bitrate_kbps: int | None = None
    format: str = "mp3"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StreamInfo:
        return cls(**data)


@dataclass
class DownloadJob:
    """State of an individual song download job."""
    song: SongEntry
    batch_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.QUEUED
    error_message: str | None = None
    match_decision: MatchDecision | None = None
    stream_info: StreamInfo | None = None
    output_path: str | None = None
    bytes_downloaded: int = 0
    total_bytes: int | None = None
    speed_bps: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def progress_fraction(self) -> float:
        if self.status == JobStatus.DONE:
            return 1.0
        if self.total_bytes and self.total_bytes > 0:
            return min(1.0, self.bytes_downloaded / self.total_bytes)
        return 0.0


@dataclass(slots=True)
class BatchSummary:
    """Aggregate report for a batch of jobs."""
    batch_id: str
    total: int
    downloaded: int
    skipped: int
    not_found: int
    failed: int
    duration_seconds: float

