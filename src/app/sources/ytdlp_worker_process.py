"""Standalone long-lived worker subprocess for yt-dlp queries."""

from __future__ import annotations

import json
import sys
from typing import Any


def run_worker() -> None:
    """Read JSON commands from stdin, execute via yt_dlp, and output JSON to stdout."""
    try:
        import yt_dlp
    except ImportError:
        sys.stderr.write("yt_dlp module is not installed.\n")
        sys.stderr.flush()
        sys.exit(1)

    ydl_search_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
        "simulate": True,
    }

    ydl_resolve_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "skip_download": True,
        "simulate": True,
    }

    ydl_search = yt_dlp.YoutubeDL(ydl_search_opts)
    ydl_resolve = yt_dlp.YoutubeDL(ydl_resolve_opts)

    # Process requests sequentially
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        resp: dict[str, Any] = {}
        try:
            req = json.loads(line)
            action = req.get("action")

            if action == "exit":
                break

            elif action == "search":
                query = req.get("query", "")
                limit = req.get("limit", 5)
                # Query via ytsearch:
                search_query = f"ytsearch{limit}:{query}"
                info = ydl_search.extract_info(search_query, download=False)
                entries = info.get("entries", []) if info else []

                candidates = []
                for e in entries:
                    if not e:
                        continue
                    candidates.append({
                        "id": e.get("id"),
                        "title": e.get("title", ""),
                        "artist": e.get("uploader") or e.get("channel"),
                        "duration": e.get("duration"),
                        "url": e.get("url") or f"https://www.youtube.com/watch?v={e.get('id')}",
                        "is_official": bool(e.get("channel_is_verified") or "topic" in (e.get("uploader") or "").lower()),
                    })
                resp = {"status": "ok", "candidates": candidates}

            elif action == "resolve":
                url = req.get("url", "")
                info = ydl_resolve.extract_info(url, download=False)
                if not info:
                    resp = {"status": "error", "message": "No stream info returned"}
                else:
                    stream_url = info.get("url")
                    fmt = info.get("ext", "m4a")
                    filesize = info.get("filesize") or info.get("filesize_approx")
                    http_headers = {str(k): str(v) for k, v in (info.get("http_headers") or {}).items()}
                    resp = {
                        "status": "ok",
                        "stream": {
                            "url": stream_url,
                            "headers": http_headers,
                            "size_bytes": filesize,
                            "format": fmt,
                            "bitrate_kbps": info.get("abr"),
                        },
                    }
            else:
                resp = {"status": "error", "message": f"Unknown action: {action}"}

        except Exception as exc:
            resp = {"status": "error", "message": str(exc)}

        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    run_worker()
