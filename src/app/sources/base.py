"""Abstract base provider interface for song search and stream resolution."""

from __future__ import annotations

import abc

from app.core.models import Candidate, StreamInfo


class SourceProvider(abc.ABC):
    """Abstract interface implemented by all audio source providers."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique provider identifier (e.g. 'archive', 'jamendo', 'mock')."""

    @property
    def is_enabled(self) -> bool:
        """Whether the provider is currently enabled in settings."""
        return True

    @abc.abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[Candidate]:
        """Search provider for candidates matching the query."""

    @abc.abstractmethod
    async def resolve(self, candidate: Candidate) -> StreamInfo:
        """Resolve a candidate to a playable/downloadable audio stream."""

