"""Direct URL audio provider for plain HTTP/HTTPS stream links."""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

from app.core.models import Candidate, StreamInfo
from app.sources.base import SourceProvider

logger = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".ogg", ".opus", ".flac", ".wav"}


class DirectURLProvider(SourceProvider):
    """Detects and resolves direct HTTP/HTTPS audio stream links."""

    def __init__(self, session: aiohttp.ClientSession | None = None) -> None:
        self.session = session

    @property
    def name(self) -> str:
        return "direct"

    async def search(self, query: str, limit: int = 10) -> list[Candidate]:
        clean_q = query.strip()
        if not (clean_q.startswith("http://") or clean_q.startswith("https://")):
            return []

        parsed = urlparse(clean_q)
        path = Path(parsed.path)
        ext = path.suffix.lower()

        # If it has an audio extension or looks like a stream URL
        title = path.stem.replace("_", " ").replace("-", " ") or "Direct Audio Stream"

        return [
            Candidate(
                provider=self.name,
                source_id=clean_q,
                title=title,
                artist="Direct Link",
                url=clean_q,
                is_official=True,
                extra={"extension": ext or ".mp3"},
            )
        ]

    async def resolve(self, candidate: Candidate) -> StreamInfo:
        url = candidate.url or candidate.source_id
        size_bytes: int | None = None
        mime = "audio/mpeg"
        etag: str | None = None

        # Inspect headers via HEAD request if session is available
        if self.session and not self.session.closed:
            try:
                async with self.session.head(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        cl = resp.headers.get("Content-Length")
                        if cl and cl.isdigit():
                            size_bytes = int(cl)
                        mime = resp.headers.get("Content-Type", "audio/mpeg").split(";")[0].strip()
                        etag = resp.headers.get("ETag")
            except Exception as e:
                logger.debug("HEAD request failed for direct URL '%s': %s", url, e)

        ext = Path(urlparse(url).path).suffix.lstrip(".").lower() or "mp3"
        return StreamInfo(
            url=url,
            headers={"User-Agent": "MusicDownloader/1.0"},
            size_bytes=size_bytes,
            mime_type=mime,
            etag=etag,
            format=ext,
        )

