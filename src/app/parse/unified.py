"""Unified document parser interface."""

from __future__ import annotations

from pathlib import Path

from app.parse.base import ParsedDocument, ParseError
from app.parse.docx_parser import parse_docx_file
from app.parse.pdf_parser import parse_pdf_file
from app.parse.text_parser import parse_csv_content, parse_raw_text


def parse_file(file_path: Path | str) -> ParsedDocument:
    """Parse any supported input file format into a ParsedDocument."""
    path = Path(file_path)
    if not path.is_file():
        raise ParseError(f"Input file not found: {path}")

    ext = path.suffix.lower()
    if ext == ".pdf":
        return parse_pdf_file(path)
    elif ext in (".docx", ".doc"):
        return parse_docx_file(path)
    elif ext in (".csv", ".tsv"):
        content = path.read_text(encoding="utf-8", errors="replace")
        return parse_csv_content(content, source_path=path)
    elif ext in (".txt", ".md", ".text"):
        content = path.read_text(encoding="utf-8", errors="replace")
        return parse_raw_text(content, source_path=path)
    else:
        # Fallback to text parsing
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            return parse_raw_text(content, source_path=path)
        except Exception as e:
            raise ParseError(f"Unsupported or unreadable file format: {ext} ({e})") from e


def parse_text_input(text: str) -> ParsedDocument:
    """Parse raw text pasted by user."""
    return parse_raw_text(text)
