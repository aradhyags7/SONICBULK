"""Unit tests for providers, provider chain fallback, and caching."""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from app.core.models import Candidate
from app.db.repository import DatabaseRepository
from app.sources.base import SourceProvider
from app.sources.cache import CachedSourceProvider
from app.sources.chain import ProviderChain
from app.sources.mock_provider import MockProvider


class FailingProvider(SourceProvider):
    """Test provider that always throws an error."""
    @property
    def name(self) -> str:
        return "failing"

    async def search(self, query: str, limit: int = 10) -> list[Candidate]:
        raise ConnectionResetError("Provider network down")

    async def resolve(self, candidate: Candidate) -> None:  # type: ignore[override]
        raise ConnectionResetError("Resolve failed")


@pytest.fixture
async def test_repo(tmp_path: Path) -> AsyncGenerator[DatabaseRepository, None]:
    repo = DatabaseRepository(tmp_path / "cache_test.db")
    await repo.initialize()
    yield repo
    await repo.close()


@pytest.mark.asyncio
async def test_mock_provider_search_and_resolve() -> None:
    provider = MockProvider(name="mock_test")
    candidates = await provider.search("Queen - Bohemian Rhapsody", limit=5)
    assert len(candidates) >= 1
    assert candidates[0].title == "Bohemian Rhapsody"
    assert candidates[0].artist == "Queen"

    stream = await provider.resolve(candidates[0])
    assert stream.url.startswith("http")
    assert stream.format == "mp3"


@pytest.mark.asyncio
async def test_provider_chain_fallback() -> None:
    failing = FailingProvider()
    working = MockProvider(name="working_mock")

    chain = ProviderChain([failing, working])
    candidates = await chain.search("Daft Punk - Get Lucky")
    # Should seamlessly fall back to working_mock
    assert len(candidates) >= 1
    assert candidates[0].title == "Get Lucky"
    assert candidates[0].provider == "working_mock"

    stream = await chain.resolve(candidates[0])
    assert stream.url is not None


@pytest.mark.asyncio
async def test_cached_source_provider(test_repo: DatabaseRepository) -> None:
    inner = MockProvider(name="mock_cache_test")
    cached = CachedSourceProvider(inner, repository=test_repo, ttl_hours=24.0)

    # First search: hits inner provider
    res1 = await cached.search("Pink Floyd - Time")
    assert inner.search_calls == 1
    assert len(res1) == 1

    # Second search with same query: must hit SQLite cache, NOT inner provider
    res2 = await cached.search("Pink Floyd - Time")
    assert inner.search_calls == 1  # Still 1!
    assert len(res2) == 1
    assert res2[0].title == res1[0].title

    # Test resolve caching
    stream1 = await cached.resolve(res1[0])
    assert inner.resolve_calls == 1

    stream2 = await cached.resolve(res1[0])
    assert inner.resolve_calls == 1  # Still 1!
    assert stream2.url == stream1.url

