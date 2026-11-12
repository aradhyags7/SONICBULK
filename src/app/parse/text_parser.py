"""Parsers for plain text, CSV, and clipboard paste content."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from app.core.models import SongEntry
from app.parse.base import ParsedDocument
from app.parse.dedupe import deduplicate_songs
from app.parse.normalizer import normalize_line
from app.parse.splitter import split_artist_title


def parse_raw_text(text: str, source_path: Path | None = None) -> ParsedDocument:
    """Parse raw multiline string into SongEntry items."""
    lines = text.splitlines()
    songs: list[SongEntry] = []
    raw_count = 0

    for raw in lines:
        raw_count += 1
        clean = normalize_line(raw)
        if not clean:
            continue
        artist, title = split_artist_title(clean)
        songs.append(SongEntry(
            raw_text=raw.strip(),
            title=title,
            artist=artist,
        ))

    deduped = deduplicate_songs(songs)
    return ParsedDocument(
        songs=deduped,
        source_path=source_path,
        total_raw_lines=raw_count,
    )


def parse_csv_content(content: str, source_path: Path | None = None) -> ParsedDocument:
    """Parse CSV content, automatically mapping artist and title columns when present."""
    reader = csv.reader(io.StringIO(content))
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        return ParsedDocument(songs=[], source_path=source_path, total_raw_lines=0)

    header = [c.strip().lower() for c in rows[0]]
    artist_idx: int | None = None
    title_idx: int | None = None

    # Detect header columns
    for idx, col in enumerate(header):
        if col in ("artist", "author", "performer", "band", "singer"):
            artist_idx = idx
        elif col in ("title", "track", "song", "name", "track_name", "song_title"):
            title_idx = idx

    songs: list[SongEntry] = []
    start_row = 1 if (artist_idx is not None or title_idx is not None) else 0

    for row in rows[start_row:]:
        if artist_idx is not None and title_idx is not None:
            raw_artist = row[artist_idx] if artist_idx < len(row) else ""
            raw_title = row[title_idx] if title_idx < len(row) else ""
            artist = normalize_line(raw_artist) or None
            title = normalize_line(raw_title)
            if title:
                raw_full = f"{raw_artist} - {raw_title}".strip(" -")
                songs.append(SongEntry(raw_text=raw_full, title=title, artist=artist))
        elif title_idx is not None and title_idx < len(row):
            clean = normalize_line(row[title_idx])
            if clean:
                artist, title = split_artist_title(clean)
                songs.append(SongEntry(raw_text=row[title_idx], title=title, artist=artist))
        else:
            # Join row cells into a text line
            line = " - ".join(cell.strip() for cell in row if cell.strip())
            clean = normalize_line(line)
            if clean:
                artist, title = split_artist_title(clean)
                songs.append(SongEntry(raw_text=line, title=title, artist=artist))

    deduped = deduplicate_songs(songs)
    return ParsedDocument(
        songs=deduped,
        source_path=source_path,
        total_raw_lines=len(rows),
    )
