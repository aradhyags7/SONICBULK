"""Adaptive concurrency controller and retry backoff calculator."""

from __future__ import annotations

import asyncio
import logging
import random
import time

logger = logging.getLogger(__name__)


def calculate_backoff(
    attempt: int,
    base: float = 1.0,
    cap: float = 60.0,
    retry_after: float | None = None,
) -> float:
    """Calculate exponential backoff with full jitter.

    If retry_after is specified, honors it as a lower bound.
    """
    if retry_after is not None and retry_after > 0:
        return retry_after

    max_sleep = min(cap, base * (2 ** attempt))
    return random.uniform(0.0, max_sleep)


class AdaptiveConcurrencyController:
    """Dynamically scales concurrency per provider/host based on 429 errors and successes."""

    def __init__(self, initial_concurrency: int = 5, min_concurrency: int = 1, max_concurrency: int = 16) -> None:
        self.min_concurrency = min_concurrency
        self.max_concurrency = max_concurrency
        self.current_limit = max(min_concurrency, min(initial_concurrency, max_concurrency))
        self._semaphore = asyncio.Semaphore(self.current_limit)
        self._consecutive_successes = 0
        self._lock = asyncio.Lock()
        self._pause_until = 0.0

    @property
    def concurrency(self) -> int:
        return self.current_limit

    async def acquire(self) -> None:
        """Acquire a slot, waiting if currently rate-limited."""
        now = time.monotonic()
        if now < self._pause_until:
            await asyncio.sleep(self._pause_until - now)
        await self._semaphore.acquire()

    def release(self) -> None:
        """Release an acquired slot."""
        try:
            self._semaphore.release()
        except ValueError:
            pass

    async def report_success(self) -> None:
        """Record successful request and gradually restore concurrency."""
        async with self._lock:
            self._consecutive_successes += 1
            if self._consecutive_successes >= 8 and self.current_limit < self.max_concurrency:
                self.current_limit += 1
                self._semaphore.release()
                self._consecutive_successes = 0
                logger.info("Adaptive concurrency increased to %d", self.current_limit)

    async def report_rate_limit(self, retry_after: float | None = None) -> None:
        """Record a 429 response, immediately reducing concurrency and applying backoff."""
        async with self._lock:
            self._consecutive_successes = 0
            old_limit = self.current_limit
            new_limit = max(self.min_concurrency, self.current_limit // 2)
            self.current_limit = new_limit
            self._semaphore = asyncio.Semaphore(self.current_limit)

            pause_sec = retry_after if (retry_after and retry_after > 0) else 2.0
            self._pause_until = max(self._pause_until, time.monotonic() + pause_sec)
            logger.warning(
                "Rate limit hit! Concurrency reduced from %d to %d, pausing for %.1fs",
                old_limit,
                new_limit,
                pause_sec,
            )
