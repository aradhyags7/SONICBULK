"""Jamendo Creative Commons audio provider using Jamendo REST API."""

from __future__ import annotations

import logging

import aiohttp

from app.core.models import Candidate, StreamInfo
from app.sources.base import SourceProvider

logger = logging.getLogger(__name__)

JAMENDO_API = "https://api.jamendo.com/v3.0/tracks/"


class JamendoProvider(SourceProvider):
    """Searches Jamendo Creative Commons music catalog and resolves direct audio streams."""

    def __init__(self, client_id: str = "a568ee4d", session: aiohttp.ClientSession | None = None) -> None:
        self.client_id = client_id
        self.session = session
        self._internal_session: aiohttp.ClientSession | None = None

    @property
    def name(self) -> str:
        return "jamendo"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session and not self.session.closed:
            return self.session
        if self._internal_session is None or self._internal_session.closed:
            self._internal_session = aiohttp.ClientSession()
        return self._internal_session

    async def close(self) -> None:
        if self._internal_session and not self._internal_session.closed:
            await self._internal_session.close()

    async def search(self, query: str, limit: int = 10) -> list[Candidate]:
        clean_q = query.strip()
        if not clean_q or clean_q.startswith("http"):
            return []

        params = {
            "client_id": self.client_id,
            "format": "json",
            "limit": str(limit),
            "namesearch": clean_q,
            "audioformat": "mp32",
        }

        session = await self._get_session()
        try:
            async with session.get(JAMENDO_API, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    logger.warning("Jamendo API returned HTTP %d", resp.status)
                    return []
                data = await resp.json()

            results = data.get("results", [])
            candidates: list[Candidate] = []
            for track in results:
                candidates.append(Candidate(
                    provider=self.name,
                    source_id=str(track.get("id")),
                    title=track.get("name", ""),
                    artist=track.get("artist_name"),
                    album=track.get("album_name"),
                    duration_seconds=float(track.get("duration", 0.0)),
                    url=track.get("audio"),
                    is_official=True,
                    extra={
                        "license_ccurl": track.get("license_ccurl"),
                        "image": track.get("image"),
                    },
                ))
            return candidates

        except Exception as e:
            logger.warning("Jamendo search failed for '%s': %s", query, e)
            return []

    async def resolve(self, candidate: Candidate) -> StreamInfo:
        audio_url = candidate.url
        if not audio_url:
            raise RuntimeError(f"Candidate '{candidate.title}' has no audio stream URL")

        return StreamInfo(
            url=audio_url,
            headers={"User-Agent": "MusicDownloader/1.0"},
            mime_type="audio/mpeg",
            format="mp3",
        )
