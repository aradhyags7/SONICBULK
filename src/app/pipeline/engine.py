"""Core multi-stage concurrent pipeline with bounded backpressure queues."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import aiohttp

from app.core.config import AppSettings
from app.core.events import BatchProgressEvent, EventBus, JobProgressEvent, JobStatusEvent
from app.core.models import (
    BatchSummary,
    Confidence,
    DownloadJob,
    JobStatus,
)
from app.db.repository import DatabaseRepository
from app.match.matcher import MatchEngine
from app.pipeline.adaptive import AdaptiveConcurrencyController
from app.pipeline.convert import convert_audio_file
from app.pipeline.download_stage import DownloadEngine
from app.pipeline.tag_stage import tag_audio_file
from app.sources.base import SourceProvider
from app.utils.paths import generate_output_path
from app.utils.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)


class PipelineEngine:
    """Orchestrates Search -> Resolve -> Download -> Tag stages concurrently with bounded queues."""

    def __init__(
        self,
        settings: AppSettings,
        repository: DatabaseRepository,
        provider: SourceProvider,
        event_bus: EventBus | None = None,
        tag_worker: Callable[[DownloadJob], Any] | None = None,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.provider = provider
        self.event_bus = event_bus or EventBus()
        self.tag_worker = tag_worker
        self.matcher = MatchEngine(
            threshold_high=settings.threshold_high,
            threshold_low=settings.threshold_low,
        )

        # Bounded queues for backpressure (flat memory usage)
        self.search_queue: asyncio.Queue[DownloadJob | None] = asyncio.Queue(maxsize=32)
        self.resolve_queue: asyncio.Queue[DownloadJob | None] = asyncio.Queue(maxsize=32)
        self.download_queue: asyncio.Queue[DownloadJob | None] = asyncio.Queue(maxsize=16)
        self.tag_queue: asyncio.Queue[DownloadJob | None] = asyncio.Queue(maxsize=32)

        # Concurrency controls
        self.download_sem = asyncio.Semaphore(settings.download_concurrency)
        self.adaptive_controller = AdaptiveConcurrencyController(
            initial_concurrency=settings.download_concurrency,
            max_concurrency=16,
        )
        self.rate_limiter = TokenBucketRateLimiter(settings.bandwidth_limit_bps)

        # Control flags and events
        self.cancel_event = asyncio.Event()
        self.pause_event = asyncio.Event()
        self.pause_event.set()  # Not paused by default

        self.session: aiohttp.ClientSession | None = None
        self.download_engine: DownloadEngine | None = None

        self._active_workers: list[asyncio.Task[None]] = []
        self._batch_id: str = ""
        self._jobs: dict[str, DownloadJob] = {}
        self._start_time: float = 0.0
        self._first_download_start_time: float | None = None

        # Statistics
        self.count_downloaded = 0
        self.count_skipped = 0
        self.count_not_found = 0
        self.count_failed = 0
        self.active_downloads_count = 0

    @property
    def time_to_first_download_sec(self) -> float | None:
        if self._first_download_start_time and self._start_time:
            return self._first_download_start_time - self._start_time
        return None

    def set_download_concurrency(self, concurrency: int) -> None:
        """Dynamically adjust download concurrency at runtime."""
        self.settings.download_concurrency = max(1, min(16, concurrency))
        # Re-initialize semaphore permits
        self.download_sem = asyncio.Semaphore(self.settings.download_concurrency)
        logger.info("Download concurrency updated to %d", self.settings.download_concurrency)

    async def initialize(self) -> None:
        """Initialize single shared aiohttp session with connection pooling and DNS cache."""
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=self.settings.per_host_limit,
            keepalive_timeout=60.0,
            ttl_dns_cache=300,
            enable_cleanup_closed=True,
        )
        self.session = aiohttp.ClientSession(connector=connector)
        self.download_engine = DownloadEngine(
            session=self.session,
            rate_limiter=self.rate_limiter,
            adaptive_controller=self.adaptive_controller,
            min_free_disk_mb=self.settings.min_disk_free_mb,
            max_retries=self.settings.max_retries,
        )

    async def close(self) -> None:
        """Close shared resources gracefully."""
        self.cancel()
        if self.session and not self.session.closed:
            await self.session.close()

    async def run_batch(self, batch_id: str, jobs: list[DownloadJob]) -> BatchSummary:
        """Execute full batch through pipeline stages."""
        if not self.session:
            await self.initialize()

        self._batch_id = batch_id
        self._jobs = {j.id: j for j in jobs}
        self._start_time = time.monotonic()
        self._first_download_start_time = None
        self.cancel_event.clear()
        self.pause_event.set()

        self.count_downloaded = 0
        self.count_skipped = 0
        self.count_not_found = 0
        self.count_failed = 0
        self.active_downloads_count = 0

        # Launch workers for each stage
        workers: list[asyncio.Task[None]] = []

        # Feeder task to push initial jobs into search queue
        feeder = asyncio.create_task(self._feeder_worker(jobs))
        workers.append(feeder)

        # Stage 1: Search / Match workers
        for _ in range(self.settings.search_concurrency):
            workers.append(asyncio.create_task(self._search_worker()))

        # Stage 2: Stream Resolve workers
        for _ in range(self.settings.resolve_concurrency):
            workers.append(asyncio.create_task(self._resolve_worker()))

        # Stage 3: Download workers
        for _ in range(self.settings.download_concurrency):
            workers.append(asyncio.create_task(self._download_worker()))

        # Stage 4: Tag & Move workers
        for _ in range(self.settings.tag_concurrency):
            workers.append(asyncio.create_task(self._tag_worker_loop()))

        self._active_workers = workers

        try:
            # Wait until all items have flowed through all queues
            await feeder
            await self.search_queue.join()
            await self.resolve_queue.join()
            await self.download_queue.join()
            await self.tag_queue.join()
        finally:
            # Send stop sentinels to terminate worker loops
            for _ in range(self.settings.search_concurrency):
                await self.search_queue.put(None)
            for _ in range(self.settings.resolve_concurrency):
                await self.resolve_queue.put(None)
            for _ in range(self.settings.download_concurrency):
                await self.download_queue.put(None)
            for _ in range(self.settings.tag_concurrency):
                await self.tag_queue.put(None)

            await asyncio.gather(*workers, return_exceptions=True)

        elapsed = time.monotonic() - self._start_time
        summary = BatchSummary(
            batch_id=batch_id,
            total=len(jobs),
            downloaded=self.count_downloaded,
            skipped=self.count_skipped,
            not_found=self.count_not_found,
            failed=self.count_failed,
            duration_seconds=elapsed,
        )
        self._publish_batch_progress()
        return summary

    async def _feeder_worker(self, jobs: list[DownloadJob]) -> None:
        """Feed jobs into bounded search queue, pausing if downstream backpressure occurs."""
        for job in jobs:
            if self.cancel_event.is_set():
                break
            await self.pause_event.wait()

            # Pre-flight duplicate check: if already completed in DB, skip!
            existing_path = await self.repository.find_completed_by_key(job.song.normalized_key)
            if existing_path and Path(existing_path).is_file():
                job.status = JobStatus.SKIPPED
                job.output_path = existing_path
                self.count_skipped += 1
                await self.repository.update_job_status(job.id, JobStatus.SKIPPED, output_path=existing_path)
                self._publish_job_status(job)
                self._publish_batch_progress()
                continue

            # Check if user marked duplicate in parsed list
            if job.song.is_duplicate:
                job.status = JobStatus.SKIPPED
                job.error_message = "Duplicate item in playlist"
                self.count_skipped += 1
                await self.repository.update_job_status(job.id, JobStatus.SKIPPED, error_message=job.error_message)
                self._publish_job_status(job)
                self._publish_batch_progress()
                continue

            await self.search_queue.put(job)

    async def _search_worker(self) -> None:
        """Stage 1: Search provider and pick best candidate."""
        while not self.cancel_event.is_set():
            await self.pause_event.wait()
            job = await self.search_queue.get()
            if job is None:
                self.search_queue.task_done()
                break

            try:
                job.status = JobStatus.SEARCHING
                await self.repository.update_job_status(job.id, JobStatus.SEARCHING)
                self._publish_job_status(job)

                candidates = await self.provider.search(job.song.query, limit=10)
                await self.repository.save_candidates(job.id, candidates)

                decision = self.matcher.match_song(job.song, candidates)
                job.match_decision = decision

                if decision.confidence == Confidence.NONE or decision.candidate is None:
                    job.status = JobStatus.NOT_FOUND
                    job.error_message = decision.reason
                    self.count_not_found += 1
                    await self.repository.update_job_status(job.id, JobStatus.NOT_FOUND, error_message=decision.reason)
                    await self.repository.save_match_decision(job.id, decision)
                    self._publish_job_status(job)
                    self._publish_batch_progress()
                else:
                    job.status = JobStatus.MATCHED
                    await self.repository.update_job_status(job.id, JobStatus.MATCHED)
                    await self.repository.save_match_decision(job.id, decision)
                    self._publish_job_status(job)

                    # Hand off immediately to Resolve queue (never wait for all searches!)
                    await self.resolve_queue.put(job)

            except Exception as e:
                logger.error("Search failed for '%s': %s", job.song.title, e)
                job.status = JobStatus.FAILED
                job.error_message = f"Search error: {e}"
                self.count_failed += 1
                await self.repository.update_job_status(job.id, JobStatus.FAILED, error_message=str(e))
                self._publish_job_status(job)
                self._publish_batch_progress()
            finally:
                self.search_queue.task_done()

    async def _resolve_worker(self) -> None:
        """Stage 2: Resolve candidate audio stream URL."""
        while not self.cancel_event.is_set():
            await self.pause_event.wait()
            job = await self.resolve_queue.get()
            if job is None:
                self.resolve_queue.task_done()
                break

            try:
                job.status = JobStatus.RESOLVING
                await self.repository.update_job_status(job.id, JobStatus.RESOLVING)
                self._publish_job_status(job)

                cand = job.match_decision.candidate if job.match_decision else None
                if not cand:
                    raise RuntimeError("No candidate to resolve")

                stream_info = await self.provider.resolve(cand)
                job.stream_info = stream_info

                # Hand off immediately to Download stage
                await self.download_queue.put(job)

            except Exception as e:
                logger.error("Resolve failed for '%s': %s", job.song.title, e)
                job.status = JobStatus.FAILED
                job.error_message = f"Stream resolution error: {e}"
                self.count_failed += 1
                await self.repository.update_job_status(job.id, JobStatus.FAILED, error_message=str(e))
                self._publish_job_status(job)
                self._publish_batch_progress()
            finally:
                self.resolve_queue.task_done()

    async def _download_worker(self) -> None:
        """Stage 3: Download audio stream with 64 KiB chunks, Range resume, and atomic rename."""
        while not self.cancel_event.is_set():
            await self.pause_event.wait()
            job = await self.download_queue.get()
            if job is None:
                self.download_queue.task_done()
                break

            if not self.download_engine or not job.stream_info:
                self.download_queue.task_done()
                continue

            async with self.download_sem:
                try:
                    if self._first_download_start_time is None:
                        self._first_download_start_time = time.monotonic()
                        logger.info("Time to first download start: %.3fs", self.time_to_first_download_sec)

                    job.status = JobStatus.DOWNLOADING
                    self.active_downloads_count += 1
                    await self.repository.update_job_status(job.id, JobStatus.DOWNLOADING)
                    self._publish_job_status(job)

                    # Compute target file path
                    dest_path = generate_output_path(
                        output_dir=self.settings.output_dir,
                        layout=self.settings.folder_layout,
                        template=self.settings.filename_template,
                        artist=job.song.artist,
                        title=job.song.title,
                        album=job.match_decision.candidate.album if job.match_decision and job.match_decision.candidate else None,
                        extension=job.stream_info.format,
                    )
                    job.output_path = str(dest_path)

                    # Check if file already exists on disk
                    if dest_path.is_file() and dest_path.stat().st_size > 0:
                        job.status = JobStatus.SKIPPED
                        self.count_skipped += 1
                        await self.repository.update_job_status(job.id, JobStatus.SKIPPED, output_path=str(dest_path))
                        self._publish_job_status(job)
                        self._publish_batch_progress()
                        continue

                    curr_job = job

                    def on_progress(bytes_down: int, total: int | None, speed: float, target_job: DownloadJob = curr_job) -> None:
                        target_job.bytes_downloaded = bytes_down
                        target_job.total_bytes = total
                        target_job.speed_bps = speed
                        self.event_bus.publish(JobProgressEvent(
                            job_id=target_job.id,
                            bytes_downloaded=bytes_down,
                            total_bytes=total,
                            speed_bps=speed,
                        ))

                    # Stream download
                    out_path = await self.download_engine.download_file(
                        job=job,
                        stream_info=job.stream_info,
                        destination_path=dest_path,
                        on_progress=on_progress,
                        cancel_event=self.cancel_event,
                    )
                    job.output_path = str(out_path)

                    # Hand off immediately to Tag stage
                    await self.tag_queue.put(job)

                except asyncio.CancelledError:
                    job.status = JobStatus.FAILED
                    job.error_message = "Cancelled"
                    await self.repository.update_job_status(job.id, JobStatus.FAILED, error_message="Cancelled")
                    self._publish_job_status(job)
                except Exception as e:
                    logger.error("Download failed for '%s': %s", job.song.title, e)
                    job.status = JobStatus.FAILED
                    job.error_message = str(e)
                    self.count_failed += 1
                    await self.repository.update_job_status(job.id, JobStatus.FAILED, error_message=str(e))
                    self._publish_job_status(job)
                    self._publish_batch_progress()
                finally:
                    self.active_downloads_count = max(0, self.active_downloads_count - 1)
                    self.download_queue.task_done()

    async def _tag_worker_loop(self) -> None:
        """Stage 4: Write audio tags (mutagen) and optional conversion."""
        while not self.cancel_event.is_set():
            await self.pause_event.wait()
            job = await self.tag_queue.get()
            if job is None:
                self.tag_queue.task_done()
                break

            try:
                job.status = JobStatus.TAGGING
                await self.repository.update_job_status(job.id, JobStatus.TAGGING)
                self._publish_job_status(job)

                if self.tag_worker:
                    await asyncio.to_thread(self.tag_worker, job)
                elif job.output_path and Path(job.output_path).is_file():
                    out_p = Path(job.output_path)
                    cand = job.match_decision.candidate if job.match_decision else None
                    album = cand.album if cand else None
                    await asyncio.to_thread(
                        tag_audio_file,
                        out_p,
                        title=job.song.title,
                        artist=job.song.artist,
                        album=album,
                    )
                    if self.settings.output_format != "native":
                        conv_p = await asyncio.to_thread(
                            convert_audio_file,
                            out_p,
                            target_format=self.settings.output_format,
                        )
                        job.output_path = str(conv_p)

                job.status = JobStatus.DONE
                self.count_downloaded += 1
                await self.repository.update_job_status(job.id, JobStatus.DONE, output_path=job.output_path)
                self._publish_job_status(job)
                self._publish_batch_progress()

            except Exception as e:
                logger.error("Tagging failed for '%s': %s", job.song.title, e)
                job.status = JobStatus.DONE  # Audio file was downloaded successfully, mark done with warning
                job.error_message = f"Tagging warning: {e}"
                self.count_downloaded += 1
                await self.repository.update_job_status(job.id, JobStatus.DONE, error_message=f"Tagging warning: {e}")
                self._publish_job_status(job)
                self._publish_batch_progress()
            finally:
                self.tag_queue.task_done()

    def _publish_job_status(self, job: DownloadJob) -> None:
        self.event_bus.publish(JobStatusEvent(
            job_id=job.id,
            status=job.status,
            error_message=job.error_message,
            output_path=job.output_path,
        ))

    def _publish_batch_progress(self) -> None:
        total = len(self._jobs)
        completed = self.count_downloaded + self.count_skipped + self.count_not_found + self.count_failed
        total_speed = sum(j.speed_bps for j in self._jobs.values() if j.status == JobStatus.DOWNLOADING)
        self.event_bus.publish(BatchProgressEvent(
            batch_id=self._batch_id,
            total=total,
            completed=completed,
            downloaded=self.count_downloaded,
            skipped=self.count_skipped,
            not_found=self.count_not_found,
            failed=self.count_failed,
            active_downloads=self.active_downloads_count,
            total_speed_bps=total_speed,
        ))

    def pause(self) -> None:
        """Pause pipeline processing."""
        self.pause_event.clear()
        logger.info("Pipeline paused")

    def resume(self) -> None:
        """Resume pipeline processing."""
        self.pause_event.set()
        logger.info("Pipeline resumed")

    def cancel(self) -> None:
        """Signal cancellation across all pipeline stages."""
        self.cancel_event.set()
        self.pause_event.set()  # Unblock paused workers so they can exit
        logger.info("Pipeline cancel requested")
