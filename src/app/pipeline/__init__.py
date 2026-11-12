"""Pipeline subpackage for concurrent search, resolve, download, and tagging stages."""

from app.pipeline.adaptive import AdaptiveConcurrencyController, calculate_backoff
from app.pipeline.download_stage import (
    CHUNK_SIZE,
    DownloadEngine,
    DownloadError,
    PermanentDownloadError,
    RetryableDownloadError,
)
from app.pipeline.engine import PipelineEngine

__all__ = [
    "PipelineEngine",
    "DownloadEngine",
    "AdaptiveConcurrencyController",
    "calculate_backoff",
    "CHUNK_SIZE",
    "DownloadError",
    "PermanentDownloadError",
    "RetryableDownloadError",
]
