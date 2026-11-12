"""YtDlpProvider using long-lived worker subprocess pool."""

from __future__ import annotations

import logging

from app.core.models import Candidate, StreamInfo
from app.sources.base import SourceProvider
from app.sources.ytdlp_pool import YtDlpWorkerPool

logger = logging.getLogger(__name__)


class YtDlpProvider(SourceProvider):
    """Optional audio provider leveraging a pool of long-lived yt-dlp worker subprocesses."""

    def __init__(self, pool: YtDlpWorkerPool | None = None, enabled: bool = False) -> None:
        self.pool = pool or YtDlpWorkerPool(pool_size=2)
        self._enabled = enabled

    @property
    def name(self) -> str:
        return "ytdlp"

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    async def search(self, query: str, limit: int = 10) -> list[Candidate]:
        if not self._enabled:
            return []

        payload = {"action": "search", "query": query, "limit": limit}
        try:
            resp = await self.pool.execute(payload)
            if resp.get("status") != "ok":
                logger.warning("yt-dlp search error: %s", resp.get("message"))
                return []

            raw_cands = resp.get("candidates", [])
            candidates: list[Candidate] = []
            for item in raw_cands:
                candidates.append(Candidate(
                    provider=self.name,
                    source_id=item["id"],
                    title=item["title"],
                    artist=item.get("artist"),
                    duration_seconds=float(item.get("duration", 0.0)) if item.get("duration") else None,
                    url=item.get("url"),
                    is_official=bool(item.get("is_official")),
                ))
            return candidates

        except Exception as e:
            logger.warning("yt-dlp search request failed for '%s': %s", query, e)
            return []

    async def resolve(self, candidate: Candidate) -> StreamInfo:
        if not self._enabled:
            raise RuntimeError("YtDlpProvider is disabled in settings")

        url = candidate.url or f"https://www.youtube.com/watch?v={candidate.source_id}"
        payload = {"action": "resolve", "url": url}

        resp = await self.pool.execute(payload)
        if resp.get("status") != "ok":
            raise RuntimeError(f"yt-dlp resolve error: {resp.get('message')}")

        stream_data = resp["stream"]
        return StreamInfo(
            url=stream_data["url"],
            headers=stream_data.get("headers", {}),
            size_bytes=stream_data.get("size_bytes"),
            mime_type=f"audio/{stream_data.get('format', 'mp3')}",
            bitrate_kbps=stream_data.get("bitrate_kbps"),
            format=stream_data.get("format", "mp3"),
        )
