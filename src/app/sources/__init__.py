"""Sources package for music search and stream resolution."""

from app.sources.base import SourceProvider
from app.sources.cache import CachedSourceProvider
from app.sources.chain import ProviderChain
from app.sources.direct import DirectURLProvider
from app.sources.internet_archive import InternetArchiveProvider
from app.sources.jamendo import JamendoProvider
from app.sources.mock_provider import MockProvider
from app.sources.ytdlp_pool import YtDlpWorkerPool
from app.sources.ytdlp_provider import YtDlpProvider

__all__ = [
    "SourceProvider",
    "CachedSourceProvider",
    "ProviderChain",
    "DirectURLProvider",
    "InternetArchiveProvider",
    "JamendoProvider",
    "MockProvider",
    "YtDlpProvider",
    "YtDlpWorkerPool",
]
