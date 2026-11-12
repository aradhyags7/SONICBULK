"""Provider fallback chain executing sources in user-configured priority order."""

from __future__ import annotations

import logging

from app.core.models import Candidate, StreamInfo
from app.sources.base import SourceProvider

logger = logging.getLogger(__name__)


class ProviderChain(SourceProvider):
    """Executes a chain of providers in prioritized order with automatic fallback."""

    def __init__(self, providers: list[SourceProvider]) -> None:
        self.providers = providers

    @property
    def name(self) -> str:
        return "chain"

    async def search(self, query: str, limit: int = 10) -> list[Candidate]:
        """Query providers in sequence until one yields matching candidates."""
        for provider in self.providers:
            if not provider.is_enabled:
                continue
            try:
                candidates = await provider.search(query, limit=limit)
                if candidates:
                    logger.debug("Provider '%s' found %d candidates for '%s'", provider.name, len(candidates), query)
                    return candidates
            except Exception as e:
                logger.warning("Provider '%s' failed for '%s' (%s), falling back to next provider", provider.name, query, e)

        logger.info("All providers exhausted for query '%s'", query)
        return []

    async def resolve(self, candidate: Candidate) -> StreamInfo:
        """Resolve candidate via its origin provider, falling back to others if needed."""
        # Find matching provider by name
        matching = [p for p in self.providers if p.name == candidate.provider and p.is_enabled]
        fallback_providers = matching + [p for p in self.providers if p not in matching and p.is_enabled]

        last_err: Exception | None = None
        for provider in fallback_providers:
            try:
                return await provider.resolve(candidate)
            except Exception as e:
                last_err = e
                logger.warning("Failed to resolve candidate '%s' via '%s': %s", candidate.title, provider.name, e)

        raise RuntimeError(f"Unable to resolve candidate '{candidate.title}' across any provider: {last_err}")
