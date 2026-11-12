"""Token-bucket rate limiter for bandwidth throttling."""

from __future__ import annotations

import asyncio
import time


class TokenBucketRateLimiter:
    """Async token bucket for limiting download bandwidth in bytes per second."""

    def __init__(self, rate_bps: int = 0) -> None:
        self.rate_bps = max(0, rate_bps)
        self._tokens = float(self.rate_bps)
        self._last_time = time.monotonic()
        self._lock = asyncio.Lock()

    def set_rate(self, rate_bps: int) -> None:
        self.rate_bps = max(0, rate_bps)
        self._tokens = min(self._tokens, float(self.rate_bps))

    async def acquire(self, num_bytes: int) -> None:
        """Wait until enough bandwidth tokens are available."""
        if self.rate_bps <= 0:
            return  # Unlimited

        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_time
            self._last_time = now

            # Refill tokens up to bucket capacity (1 second buffer)
            self._tokens = min(float(self.rate_bps), self._tokens + elapsed * self.rate_bps)

            if self._tokens >= num_bytes:
                self._tokens -= num_bytes
                return

            # Need to sleep to accumulate enough tokens
            deficit = num_bytes - self._tokens
            sleep_duration = deficit / self.rate_bps
            self._tokens = 0.0

        await asyncio.sleep(sleep_duration)

