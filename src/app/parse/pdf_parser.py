"""PDF parser supporting multi-column layout, table extraction, header/footer stripping, and scanned detection."""

from __future__ import annotations

import collections
import logging
import re
from pathlib import Path
from typing import Any

from app.core.models import SongEntry
from app.parse.base import ParsedDocument, ScannedDocumentError
from app.parse.dedupe import deduplicate_songs
from app.parse.normalizer import normalize_line
from app.parse.splitter import split_artist_title

logger = logging.getLogger(__name__)

_RE_PAGE_NUM = re.compile(
    r"^(?:page\s+\d+(?:\s*(?:of|/)\s*\d+)?|\d+\s*/\s*\d+|\d+)$",
    re.IGNORECASE,
)


def _extract_page_words_layout(page: Any) -> list[str]:
    """Extract text from a pdfplumber page, handling multi-column layouts cleanly."""
    words = page.extract_words(keep_blank_chars=False)
    if not words:
        text = page.extract_text() or ""
        return [line.strip() for line in text.splitlines() if line.strip()]

    page_width = float(page.width)
    mid_point = page_width / 2.0

    # Check for 2-column distribution: words in left (x0 < mid - 20) and right (x0 > mid + 20)
    # with a dead zone/gutter in the middle
    left_words = [w for w in words if w["x1"] < mid_point]
    right_words = [w for w in words if w["x0"] >= mid_point]

    is_two_column = False
    if len(left_words) > 5 and len(right_words) > 5:
        # Check if there is vertical overlap (meaning both columns are populated simultaneously)
        left_tops = [w["top"] for w in left_words]
        right_tops = [w["top"] for w in right_words]
        if min(left_tops) < max(right_tops) and min(right_tops) < max(left_tops):
            is_two_column = True

    columns: list[list[dict[str, Any]]] = []
    if is_two_column:
        columns.append(sorted(left_words, key=lambda w: (w["top"], w["x0"])))
        columns.append(sorted(right_words, key=lambda w: (w["top"], w["x0"])))
    else:
        columns.append(sorted(words, key=lambda w: (w["top"], w["x0"])))

    page_lines: list[str] = []
    line_tolerance = 4.0

    for col in columns:
        current_line: list[dict[str, Any]] = []
        current_top: float | None = None

        for w in col:
            if current_top is None:
                current_top = w["top"]
                current_line.append(w)
            elif abs(w["top"] - current_top) <= line_tolerance:
                current_line.append(w)
            else:
                # Flush line
                current_line.sort(key=lambda item: item["x0"])
                text_line = " ".join(item["text"] for item in current_line).strip()
                if text_line:
                    page_lines.append(text_line)
                current_line = [w]
                current_top = w["top"]

        if current_line:
            current_line.sort(key=lambda item: item["x0"])
            text_line = " ".join(item["text"] for item in current_line).strip()
            if text_line:
                page_lines.append(text_line)

    return page_lines


def parse_pdf_file(file_path: Path | str) -> ParsedDocument:
    """Extract songs from a PDF file with multi-column support and scanned detection."""
    path = Path(file_path)
    all_page_lines: list[list[str]] = []
    total_chars = 0
    warnings: list[str] = []

    try:
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            for _page_idx, page in enumerate(pdf.pages):
                # 1. Extract tables
                try:
                    tables = page.extract_tables()
                    for t in tables:
                        for row in t:
                            cells = [c.strip() for c in row if c and c.strip()]
                            if cells:
                                line = " - ".join(cells)
                                all_page_lines.append([line])
                                total_chars += len(line)
                except Exception:
                    pass

                # 2. Extract layout-aware words
                lines = _extract_page_words_layout(page)
                page_chars = sum(len(line) for line in lines)
                total_chars += page_chars
                all_page_lines.append(lines)

    except Exception as e:
        logger.warning("pdfplumber failed (%s), falling back to pypdf", e)
        warnings.append(f"pdfplumber fallback: {e}")
        try:
            import pypdf

            reader = pypdf.PdfReader(str(path))
            for page_obj in reader.pages:
                text = page_obj.extract_text() or ""
                extracted_lines = [line.strip() for line in text.splitlines() if line.strip()]
                total_chars += sum(len(line) for line in extracted_lines)
                all_page_lines.append(extracted_lines)
        except Exception as pypdf_err:
            raise ScannedDocumentError(
                f"Failed to read PDF document: {pypdf_err}"
            ) from pypdf_err

    # Check for scanned PDF with no text layer
    if total_chars < 20:
        raise ScannedDocumentError(
            "Scanned PDF detected with no selectable text layer. "
            "Please provide a text-based document or OCR-processed PDF."
        )

    # Detect repeating headers/footers across pages
    header_counts: collections.Counter[str] = collections.Counter()
    footer_counts: collections.Counter[str] = collections.Counter()
    num_pages = len(all_page_lines)

    if num_pages >= 3:
        for p_lines in all_page_lines:
            if p_lines:
                header_counts[p_lines[0]] += 1
            if len(p_lines) > 1:
                footer_counts[p_lines[-1]] += 1

    repeated_headers = {
        line for line, count in header_counts.items() if count >= (num_pages * 0.6)
    }
    repeated_footers = {
        line for line, count in footer_counts.items() if count >= (num_pages * 0.6)
    }

    # Flatten and filter lines
    songs: list[SongEntry] = []
    raw_lines_count = 0

    for p_lines in all_page_lines:
        for line in p_lines:
            raw_lines_count += 1
            # Skip page numbers
            if _RE_PAGE_NUM.match(line):
                continue
            # Skip repeated header / footer
            if line in repeated_headers or line in repeated_footers:
                continue

            clean = normalize_line(line)
            if not clean:
                continue

            artist, title = split_artist_title(clean)
            songs.append(SongEntry(raw_text=line, title=title, artist=artist))

    deduped = deduplicate_songs(songs)
    return ParsedDocument(
        songs=deduped,
        warnings=warnings,
        source_path=path,
        total_raw_lines=raw_lines_count,
    )
