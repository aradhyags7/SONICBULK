"""DOCX document parser for song lists and tables."""

from __future__ import annotations

from pathlib import Path

import docx

from app.core.models import SongEntry
from app.parse.base import ParsedDocument
from app.parse.dedupe import deduplicate_songs
from app.parse.normalizer import normalize_line
from app.parse.splitter import split_artist_title


def parse_docx_file(file_path: Path | str) -> ParsedDocument:
    """Extract songs from DOCX paragraphs and tables."""
    path = Path(file_path)
    doc = docx.Document(str(path))
    lines: list[str] = []

    # 1. Extract paragraphs
    for p in doc.paragraphs:
        t = p.text.strip()
        if t:
            lines.append(t)

    # 2. Extract tables
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                # Deduplicate identical adjacent cells (due to merged cells)
                unique_cells: list[str] = []
                for c in cells:
                    if not unique_cells or unique_cells[-1] != c:
                        unique_cells.append(c)
                lines.append(" - ".join(unique_cells))

    songs: list[SongEntry] = []
    for raw in lines:
        clean = normalize_line(raw)
        if not clean:
            continue
        artist, title = split_artist_title(clean)
        songs.append(SongEntry(raw_text=raw, title=title, artist=artist))

    deduped = deduplicate_songs(songs)
    return ParsedDocument(
        songs=deduped,
        source_path=path,
        total_raw_lines=len(lines),
    )
