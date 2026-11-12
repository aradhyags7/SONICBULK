"""Local aiohttp test server providing Range, ETag, Retry-After, disconnects, and 100 fake songs."""

from __future__ import annotations

import collections
from typing import Any

from aiohttp import web

# Deterministic test payload: 256 KiB
SONG_DATA = bytes([(i % 256) for i in range(256 * 1024)])
SONG_ETAG = '"test-song-etag-v1"'


class MockAudioServer:
    """Mock HTTP audio server for testing download engine, resume, and edge cases."""

    def __init__(self) -> None:
        self.flaky_counts: collections.Counter[str] = collections.Counter()
        self.rate_limit_hits = 0
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self) -> None:
        self.app.router.add_get("/songs/{song_id}", self.handle_song)
        self.app.router.add_get("/flaky/{song_id}", self.handle_flaky)
        self.app.router.add_get("/rate-limit/{song_id}", self.handle_rate_limit)
        self.app.router.add_get("/disconnect/{song_id}", self.handle_disconnect)
        self.app.router.add_get("/range-416/{song_id}", self.handle_416)
        self.app.router.add_get("/catalog", self.handle_catalog)

    async def handle_song(self, request: web.Request) -> web.StreamResponse:
        total = len(SONG_DATA)
        range_header = request.headers.get("Range")
        if_range = request.headers.get("If-Range")

        # Check If-Range
        if if_range and if_range != SONG_ETAG:
            # Mismatch: must return full file with 200 OK
            response = web.Response(
                body=SONG_DATA,
                status=200,
                headers={
                    "Content-Type": "audio/mpeg",
                    "Content-Length": str(total),
                    "ETag": SONG_ETAG,
                    "Accept-Ranges": "bytes",
                },
            )
            return response

        if range_header and range_header.startswith("bytes="):
            # Parse Range: bytes=start-end
            parts = range_header[6:].split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if len(parts) > 1 and parts[1] else total - 1
            start = min(start, total)
            end = min(end, total - 1)

            if start > end:
                return web.Response(
                    status=416,
                    headers={"Content-Range": f"bytes */{total}"},
                )

            chunk = SONG_DATA[start:end + 1]
            response = web.Response(
                body=chunk,
                status=206,
                headers={
                    "Content-Type": "audio/mpeg",
                    "Content-Range": f"bytes {start}-{end}/{total}",
                    "Content-Length": str(len(chunk)),
                    "ETag": SONG_ETAG,
                    "Accept-Ranges": "bytes",
                },
            )
            return response

        return web.Response(
            body=SONG_DATA,
            status=200,
            headers={
                "Content-Type": "audio/mpeg",
                "Content-Length": str(total),
                "ETag": SONG_ETAG,
                "Accept-Ranges": "bytes",
            },
        )

    async def handle_flaky(self, request: web.Request) -> web.Response:
        song_id = request.match_info["song_id"]
        self.flaky_counts[song_id] += 1
        if self.flaky_counts[song_id] < 3:
            return web.Response(status=503, text="Service Temporarily Unavailable", headers={"Retry-After": "0.1"})
        return web.Response(body=SONG_DATA, status=200, headers={"Content-Length": str(len(SONG_DATA))})

    async def handle_rate_limit(self, request: web.Request) -> web.Response:
        self.rate_limit_hits += 1
        if self.rate_limit_hits <= 1:
            return web.Response(status=429, text="Too Many Requests", headers={"Retry-After": "0.2"})
        return web.Response(body=SONG_DATA, status=200, headers={"Content-Length": str(len(SONG_DATA))})

    async def handle_disconnect(self, request: web.Request) -> web.StreamResponse:
        # Send 32 KiB and abruptly terminate without closing cleanly
        resp = web.StreamResponse(
            status=200,
            headers={"Content-Type": "audio/mpeg", "Content-Length": str(len(SONG_DATA))},
        )
        await resp.prepare(request)
        await resp.write(SONG_DATA[:32 * 1024])
        # Force transport close
        if request.transport:
            request.transport.close()
        return resp

    async def handle_416(self, request: web.Request) -> web.Response:
        total = len(SONG_DATA)
        return web.Response(
            status=416,
            headers={"Content-Range": f"bytes */{total}"},
        )

    async def handle_catalog(self, request: web.Request) -> web.Response:
        songs: list[dict[str, Any]] = [
            {
                "id": f"song-{i:03d}",
                "title": f"Test Track {i}",
                "artist": f"Artist {i % 10}",
                "album": f"Album {i // 10}",
                "duration": 180 + (i % 60),
                "url": f"/songs/song-{i:03d}",
            }
            for i in range(100)
        ]
        return web.json_response({"songs": songs, "total": 100})
