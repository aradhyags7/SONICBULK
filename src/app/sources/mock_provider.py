"""Mock audio provider for offline testing and benchmarking."""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.models import Candidate, StreamInfo
from app.sources.base import SourceProvider


class MockProvider(SourceProvider):
    """Deterministic mock provider returning test candidates and streams."""

    def __init__(
        self,
        name: str = "mock",
        base_stream_url: str = "http://127.0.0.1:8000/songs/song-001",
        search_latency: float = 0.01,
        resolve_latency: float = 0.01,
        catalog: list[dict[str, Any]] | None = None,
    ) -> None:
        self._name = name
        self.base_stream_url = base_stream_url
        self.search_latency = search_latency
        self.resolve_latency = resolve_latency
        self.catalog = catalog or []
        self.search_calls = 0
        self.resolve_calls = 0

    @property
    def name(self) -> str:
        return self._name

    async def search(self, query: str, limit: int = 10) -> list[Candidate]:
        self.search_calls += 1
        if self.search_latency > 0:
            await asyncio.sleep(self.search_latency)

        if self.catalog:
            results: list[Candidate] = []
            q_lower = query.lower()
            for item in self.catalog:
                title = item.get("title", "")
                artist = item.get("artist", "")
                if q_lower in title.lower() or q_lower in artist.lower() or not query.strip():
                    results.append(Candidate(
                        provider=self.name,
                        source_id=item.get("id", f"mock-{len(results)}"),
                        title=title,
                        artist=artist,
                        album=item.get("album"),
                        duration_seconds=float(item.get("duration", 210.0)),
                        url=item.get("url", self.base_stream_url),
                        is_official=True,
                    ))
                if len(results) >= limit:
                    break
            if results:
                return results

        # Synthesize a realistic high-match candidate for the query
        parts = query.split(" - ", 1)
        artist = parts[0].strip() if len(parts) == 2 else "Artist"
        title = parts[1].strip() if len(parts) == 2 else query.strip()

        return [
            Candidate(
                provider=self.name,
                source_id=f"mock-{hash(query) % 10000}",
                title=title,
                artist=artist,
                album="Mock Album",
                duration_seconds=215.0,
                url=self.base_stream_url,
                is_official=True,
                is_verified=True,
            )
        ]

    async def resolve(self, candidate: Candidate) -> StreamInfo:
        self.resolve_calls += 1
        if self.resolve_latency > 0:
            await asyncio.sleep(self.resolve_latency)

        stream_url = candidate.url or self.base_stream_url
        return StreamInfo(
            url=stream_url,
            headers={"User-Agent": "MusicDownloader/1.0"},
            size_bytes=262144,
            mime_type="audio/mpeg",
            etag='"mock-etag-v1"',
            format="mp3",
        )
