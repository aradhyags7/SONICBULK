"""TTL-based caching decorator for SourceProvider search and stream resolution."""

from __future__ import annotations

import logging

from app.core.models import Candidate, StreamInfo
from app.db.repository import DatabaseRepository
from app.sources.base import SourceProvider

logger = logging.getLogger(__name__)


class CachedSourceProvider(SourceProvider):
    """Wraps a SourceProvider with persistent SQLite TTL caching."""

    def __init__(self, provider: SourceProvider, repository: DatabaseRepository, ttl_hours: float = 24.0) -> None:
        self.provider = provider
        self.repository = repository
        self.ttl_seconds = ttl_hours * 3600.0

    @property
    def name(self) -> str:
        return self.provider.name

    @property
    def is_enabled(self) -> bool:
        return self.provider.is_enabled

    async def search(self, query: str, limit: int = 10) -> list[Candidate]:
        clean_q = query.strip().lower()
        cache_key = f"search:{self.provider.name}:{clean_q}:{limit}"
        cached_data = await self.repository.get_cache(cache_key)

        if cached_data is not None and isinstance(cached_data, list):
            logger.debug("Cache hit for search '%s'", query)
            return [Candidate.from_dict(item) for item in cached_data]

        candidates = await self.provider.search(query, limit=limit)
        serialized = [c.to_dict() for c in candidates]
        await self.repository.set_cache(cache_key, "search", serialized, self.ttl_seconds)
        return candidates

    async def resolve(self, candidate: Candidate) -> StreamInfo:
        cache_key = f"resolve:{candidate.provider}:{candidate.source_id}"
        cached_data = await self.repository.get_cache(cache_key)

        if cached_data is not None and isinstance(cached_data, dict):
            logger.debug("Cache hit for stream resolve '%s'", candidate.title)
            return StreamInfo.from_dict(cached_data)

        stream_info = await self.provider.resolve(candidate)
        await self.repository.set_cache(cache_key, "resolve", stream_info.to_dict(), self.ttl_seconds)
        return stream_info
