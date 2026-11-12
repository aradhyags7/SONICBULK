"""Long-lived worker subprocess pool for yt-dlp queries with isolated crash recovery."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

WORKER_SCRIPT = Path(__file__).parent / "ytdlp_worker_process.py"


class YtDlpWorker:
    """Manages an individual long-lived yt-dlp worker subprocess."""

    def __init__(self, proc: asyncio.subprocess.Process) -> None:
        self.proc = proc

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send command and read JSON line response."""
        if self.proc.returncode is not None or self.proc.stdin is None or self.proc.stdout is None:
            raise RuntimeError("Subprocess is not running")

        line = json.dumps(payload) + "\n"
        self.proc.stdin.write(line.encode("utf-8"))
        await self.proc.stdin.drain()

        resp_line = await self.proc.stdout.readline()
        if not resp_line:
            raise EOFError("Worker subprocess terminated unexpectedly")

        return json.loads(resp_line.decode("utf-8"))

    async def terminate(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.write(b'{"action":"exit"}\n')
                await self.proc.stdin.drain()
            await asyncio.wait_for(self.proc.wait(), timeout=1.0)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass


class YtDlpWorkerPool:
    """Maintains a pool of long-lived yt-dlp subprocesses, isolating crashes."""

    def __init__(self, pool_size: int = 2) -> None:
        self.pool_size = max(1, pool_size)
        self._queue: asyncio.Queue[YtDlpWorker] = asyncio.Queue()
        self._all_workers: list[YtDlpWorker] = []
        self._is_running = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Spawn initial worker subprocesses."""
        async with self._lock:
            if self._is_running:
                return
            self._is_running = True

            for _ in range(self.pool_size):
                worker = await self._spawn_worker()
                self._all_workers.append(worker)
                await self._queue.put(worker)

            logger.info("YtDlpWorkerPool started with %d workers", self.pool_size)

    async def _spawn_worker(self) -> YtDlpWorker:
        """Spawn a new worker subprocess using current python executable."""
        env = dict(os.environ)
        src_path = str(Path(__file__).resolve().parent.parent.parent)
        env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(WORKER_SCRIPT),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env=env,
        )
        return YtDlpWorker(proc)

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute request on an available worker, recovering if worker dies."""
        if not self._is_running:
            await self.start()

        worker = await self._queue.get()
        try:
            return await worker.execute(payload)
        except Exception as e:
            logger.warning("yt-dlp worker failed (%s); respawning replacement worker", e)
            await worker.terminate()
            if worker in self._all_workers:
                self._all_workers.remove(worker)

            # Spawn replacement worker to keep pool size constant
            replacement = await self._spawn_worker()
            self._all_workers.append(replacement)
            worker = replacement
            raise RuntimeError(f"yt-dlp command failed: {e}") from e
        finally:
            await self._queue.put(worker)

    async def close(self) -> None:
        """Terminate all worker subprocesses."""
        async with self._lock:
            self._is_running = False
            for w in self._all_workers:
                await w.terminate()
            self._all_workers.clear()
            logger.info("YtDlpWorkerPool shut down")
