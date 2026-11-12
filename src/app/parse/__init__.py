"""Parsing subpackage for PDF, DOCX, CSV, and text song lists."""

from app.parse.base import ParsedDocument, ParseError, ScannedDocumentError
from app.parse.dedupe import canonical_key, deduplicate_songs
from app.parse.normalizer import normalize_line
from app.parse.splitter import split_artist_title
from app.parse.unified import parse_file, parse_text_input

__all__ = [
    "ParsedDocument",
    "ParseError",
    "ScannedDocumentError",
    "canonical_key",
    "deduplicate_songs",
    "normalize_line",
    "split_artist_title",
    "parse_file",
    "parse_text_input",
]

