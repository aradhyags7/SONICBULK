"""Internet Archive audio provider querying Archive.org APIs."""

from __future__ import annotations

import logging
import urllib.parse
from typing import Any

import aiohttp

from app.core.models import Candidate, StreamInfo
from app.sources.base import SourceProvider

logger = logging.getLogger(__name__)

SEARCH_API = "https://archive.org/advancedsearch.php"
METADATA_API = "https://archive.org/metadata"


class InternetArchiveProvider(SourceProvider):
    """Searches archive.org audio collections and resolves direct audio file downloads."""

    def __init__(self, session: aiohttp.ClientSession | None = None) -> None:
        self.session = session
        self._internal_session: aiohttp.ClientSession | None = None

    @property
    def name(self) -> str:
        return "archive"

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

        # Sanitize query for Lucene syntax
        safe_q = clean_q.replace('"', '\\"').replace(":", " ")
        q_expr = f'mediatype:(audio) AND ("{safe_q}")'
        params = {
            "q": q_expr,
            "fl[]": "identifier,title,creator,album,year",
            "rows": str(limit),
            "output": "json",
        }

        session = await self._get_session()
        try:
            async with session.get(SEARCH_API, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    logger.warning("Archive.org search returned HTTP %d", resp.status)
                    return []
                data = await resp.json()

            docs = data.get("response", {}).get("docs", [])
            candidates: list[Candidate] = []
            for doc in docs:
                ident = doc.get("identifier")
                title = doc.get("title") or ident
                creator = doc.get("creator")
                if isinstance(creator, list):
                    creator = ", ".join(creator)
                album = doc.get("album")
                if isinstance(album, list):
                    album = album[0]

                candidates.append(Candidate(
                    provider=self.name,
                    source_id=ident,
                    title=str(title),
                    artist=str(creator) if creator else None,
                    album=str(album) if album else None,
                    is_official=True,
                ))
            return candidates

        except Exception as e:
            logger.warning("Internet Archive search failed for '%s': %s", query, e)
            return []

    async def resolve(self, candidate: Candidate) -> StreamInfo:
        ident = candidate.source_id
        url = f"{METADATA_API}/{ident}"
        session = await self._get_session()

        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Archive.org metadata returned HTTP {resp.status}")
            data = await resp.json()

        files: list[dict[str, Any]] = data.get("files", [])
        # Look for best MP3 / audio file
        best_file: dict[str, Any] | None = None
        for f in files:
            fmt = str(f.get("format", "")).lower()
            name = str(f.get("name", "")).lower()
            if "vbr mp3" in fmt or name.endswith(".mp3"):
                best_file = f
                break
            elif "flac" in fmt or name.endswith(".flac"):
                best_file = f
            elif "ogg" in fmt or name.endswith(".ogg"):
                if not best_file:
                    best_file = f

        if not best_file:
            raise RuntimeError(f"No suitable audio stream found in Archive.org item '{ident}'")

        file_name = best_file["name"]
        safe_name = urllib.parse.quote(file_name)
        stream_url = f"https://archive.org/download/{ident}/{safe_name}"

        size_bytes = None
        if "size" in best_file and str(best_file["size"]).isdigit():
            size_bytes = int(best_file["size"])

        ext = file_name.split(".")[-1].lower() if "." in file_name else "mp3"
        return StreamInfo(
            url=stream_url,
            headers={"User-Agent": "MusicDownloader/1.0"},
            size_bytes=size_bytes,
            mime_type="audio/mpeg" if ext == "mp3" else f"audio/{ext}",
            etag=best_file.get("md5"),
            format=ext,
        )
