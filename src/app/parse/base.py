"""Base types and exceptions for document parsing."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.core.models import SongEntry


class ParseError(Exception):
    """General document parsing error."""


class ScannedDocumentError(ParseError):
    """Raised when a document appears to be a scanned image with no text layer."""


@dataclass
class ParsedDocument:
    """Result of parsing a file or text block into songs."""
    songs: list[SongEntry]
    warnings: list[str] = field(default_factory=list)
    source_path: Path | None = None
    is_scanned: bool = False
    total_raw_lines: int = 0

