"""Streaming download engine with Range resume, atomic rename, and adaptive retries."""

from __future__ import annotations

import asyncio
import email.utils
import logging
import os
from pathlib import Path
from typing import Callable

import aiohttp

from app.core.models import DownloadJob, StreamInfo
from app.pipeline.adaptive import AdaptiveConcurrencyController, calculate_backoff
from app.utils.disk import check_disk_space
from app.utils.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)

CHUNK_SIZE = 64 * 1024  # 64 KiB chunks


class DownloadError(Exception):
    """Base exception for download failures."""


class PermanentDownloadError(DownloadError):
    """Non-retryable error (e.g. 404 Not Found, 403 Forbidden, Disk Full)."""


class RetryableDownloadError(DownloadError):
    """Temporary failure eligible for retry (e.g. 5xx, timeouts, socket drops)."""


class RateLimitError(RetryableDownloadError):
    """429 Too Many Requests with optional Retry-After header."""
    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


def parse_retry_after(header_val: str | None) -> float | None:
    """Parse HTTP Retry-After header (seconds or RFC 2822 date)."""
    if not header_val:
        return None
    try:
        return float(header_val.strip())
    except ValueError:
        pass
    try:
        dt = email.utils.parsedate_to_datetime(header_val)
        delay = (dt.timestamp() - asyncio.get_event_loop().time())
        return max(0.0, delay)
    except Exception:
        return None


class DownloadEngine:
    """Production download engine managing streams, resumes, and retries."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        rate_limiter: TokenBucketRateLimiter | None = None,
        adaptive_controller: AdaptiveConcurrencyController | None = None,
        min_free_disk_mb: int = 500,
        max_retries: int = 6,
    ) -> None:
        self.session = session
        self.rate_limiter = rate_limiter or TokenBucketRateLimiter(0)
        self.adaptive_controller = adaptive_controller or AdaptiveConcurrencyController()
        self.min_free_disk_mb = min_free_disk_mb
        self.max_retries = max_retries

    async def download_file(
        self,
        job: DownloadJob,
        stream_info: StreamInfo,
        destination_path: Path,
        on_progress: Callable[[int, int | None, float], None] | None = None,
        cancel_event: asyncio.Event | None = None,
    ) -> Path:
        """Download audio file to destination_path using .part file and atomic rename.

        Guarantees:
        - 64 KiB chunk streaming directly to disk (never buffers entire file in RAM)
        - Resumes partial download using Range + If-Range (ETag or Last-Modified)
        - 200 instead of 206 -> restarts from zero
        - 416 -> checks file completeness or restarts from zero
        - Exponential backoff with full jitter on retryable failures
        - Pre-flight disk space verification
        - Physical fsync and atomic rename on completion
        - Cancel without file corruption
        """
        dest = Path(destination_path).resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        part_path = dest.with_name(f"{dest.name}.part")

        # Pre-flight disk space check
        sufficient, free_mb = check_disk_space(dest.parent, self.min_free_disk_mb)
        if not sufficient:
            raise PermanentDownloadError(
                f"Disk space low ({free_mb} MB available, requires {self.min_free_disk_mb} MB)"
            )

        attempt = 0
        while True:
            try:
                await self.adaptive_controller.acquire()
                try:
                    return await self._download_attempt(
                        job=job,
                        stream_info=stream_info,
                        dest=dest,
                        part_path=part_path,
                        on_progress=on_progress,
                        cancel_event=cancel_event,
                    )
                finally:
                    self.adaptive_controller.release()

            except RateLimitError as rle:
                await self.adaptive_controller.report_rate_limit(rle.retry_after)
                attempt += 1
                if attempt > self.max_retries:
                    raise PermanentDownloadError(f"Exceeded max retries ({self.max_retries}): {rle}") from rle
                delay = calculate_backoff(attempt, retry_after=rle.retry_after)
                logger.warning("Rate limit hit for %s, retrying in %.2fs (attempt %d)", job.song.title, delay, attempt)
                await asyncio.sleep(delay)

            except RetryableDownloadError as rde:
                attempt += 1
                if attempt > self.max_retries:
                    raise PermanentDownloadError(f"Exceeded max retries ({self.max_retries}): {rde}") from rde
                delay = calculate_backoff(attempt)
                logger.warning("Retryable error downloading %s: %s (attempt %d, waiting %.2fs)", job.song.title, rde, attempt, delay)
                await asyncio.sleep(delay)

            except PermanentDownloadError:
                raise
            except asyncio.CancelledError:
                logger.info("Download cancelled for %s", job.song.title)
                raise
            except Exception as e:
                # Catch unexpected connection drop / socket errors as retryable
                attempt += 1
                if attempt > self.max_retries:
                    raise PermanentDownloadError(f"Download failed after {self.max_retries} retries: {e}") from e
                delay = calculate_backoff(attempt)
                logger.warning("Unexpected error downloading %s: %s (retrying in %.2fs)", job.song.title, e, delay)
                await asyncio.sleep(delay)

    async def _download_attempt(
        self,
        job: DownloadJob,
        stream_info: StreamInfo,
        dest: Path,
        part_path: Path,
        on_progress: Callable[[int, int | None, float], None] | None,
        cancel_event: asyncio.Event | None,
    ) -> Path:
        headers = dict(stream_info.headers)
        resume_offset = 0

        # Check existing .part file for resume
        if part_path.is_file():
            resume_offset = part_path.stat().st_size
            if resume_offset > 0:
                headers["Range"] = f"bytes={resume_offset}-"
                if stream_info.etag:
                    headers["If-Range"] = stream_info.etag
                elif stream_info.last_modified:
                    headers["If-Range"] = stream_info.last_modified

        timeout = aiohttp.ClientTimeout(total=300, sock_read=30, sock_connect=15)
        try:
            async with self.session.get(stream_info.url, headers=headers, timeout=timeout) as response:
                status = response.status

                # Handle 429 Too Many Requests
                if status == 429:
                    retry_after = parse_retry_after(response.headers.get("Retry-After"))
                    raise RateLimitError("HTTP 429 Too Many Requests", retry_after=retry_after)

                # Handle 503 Service Unavailable
                if status == 503:
                    retry_after = parse_retry_after(response.headers.get("Retry-After"))
                    raise RetryableDownloadError(f"HTTP 503 Service Unavailable (Retry-After: {retry_after})")

                # Handle permanent HTTP errors
                if status in (400, 401, 403, 404, 410):
                    raise PermanentDownloadError(f"Permanent HTTP error {status}: {response.reason}")

                # Handle 416 Range Not Satisfiable
                if status == 416:
                    cr = response.headers.get("Content-Range", "")
                    # Content-Range format: bytes */total
                    if "/" in cr:
                        total_str = cr.split("/")[-1].strip()
                        if total_str.isdigit() and int(total_str) == resume_offset and resume_offset > 0:
                            # Already fully downloaded!
                            part_path.replace(dest)
                            await self.adaptive_controller.report_success()
                            return dest
                    # Invalid range: wipe .part and restart
                    if part_path.is_file():
                        part_path.unlink(missing_ok=True)
                    raise RetryableDownloadError("HTTP 416 Range Not Satisfiable: restarting from zero")

                # Handle other 5xx server errors
                if status >= 500:
                    raise RetryableDownloadError(f"Server error HTTP {status}: {response.reason}")

                if status not in (200, 206):
                    raise PermanentDownloadError(f"Unexpected HTTP status {status}: {response.reason}")

                # If server sent 200 instead of 206, Range was not honored or If-Range failed -> start from 0
                mode = "ab"
                bytes_downloaded = resume_offset
                if status == 200:
                    mode = "wb"
                    bytes_downloaded = 0

                # Determine total size
                content_len = response.headers.get("Content-Length")
                total_bytes = stream_info.size_bytes
                if content_len and content_len.isdigit():
                    if status == 206:
                        total_bytes = bytes_downloaded + int(content_len)
                    else:
                        total_bytes = int(content_len)

                # Open .part file for writing/appending
                with open(part_path, mode) as f:
                    start_time = asyncio.get_event_loop().time()
                    last_progress_time = start_time
                    chunk_bytes_since_last = 0
                    speed_bps = 0.0

                    async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                        if cancel_event and cancel_event.is_set():
                            # Flush file descriptor, do NOT delete .part so resume is retained
                            f.flush()
                            os.fsync(f.fileno())
                            raise asyncio.CancelledError("Download cancelled by user")

                        # Bandwidth throttling
                        await self.rate_limiter.acquire(len(chunk))

                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                        chunk_bytes_since_last += len(chunk)

                        now = asyncio.get_event_loop().time()
                        dt = now - last_progress_time
                        # Notify on first chunk or every 0.2s (5 Hz throttling)
                        if dt >= 0.2 or bytes_downloaded == len(chunk):
                            speed_bps = chunk_bytes_since_last / max(0.001, dt)
                            chunk_bytes_since_last = 0
                            last_progress_time = now
                            if on_progress:
                                on_progress(bytes_downloaded, total_bytes, speed_bps)

                    # Flush and physical fsync to ensure data integrity
                    f.flush()
                    os.fsync(f.fileno())

                # Validate downloaded size if total_bytes was known
                final_size = part_path.stat().st_size
                if total_bytes and total_bytes > 0 and final_size < total_bytes:
                    raise RetryableDownloadError(
                        f"Premature stream end: downloaded {final_size} of {total_bytes} bytes"
                    )

                # Atomic rename from .part to destination
                part_path.replace(dest)

                # Final 100% progress notification
                if on_progress:
                    on_progress(final_size, total_bytes or final_size, speed_bps)

                await self.adaptive_controller.report_success()
                return dest

        except (aiohttp.ClientError, asyncio.TimeoutError) as net_err:
            raise RetryableDownloadError(f"Network error: {net_err}") from net_err
