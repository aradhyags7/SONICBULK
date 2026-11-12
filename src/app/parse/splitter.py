"""Split normalized song text into artist and title components."""

from __future__ import annotations

import re

# Match "by" as a word separator: e.g. "Bohemian Rhapsody by Queen"
_RE_BY_SEP = re.compile(r"\s+\bby\b\s+", re.IGNORECASE)

# Dash variants: en-dash, em-dash, standard hyphen surrounded by spaces
_DASH_DELIMITERS = [" - ", " – ", " — ", " | "]


def split_artist_title(line: str) -> tuple[str | None, str]:
    """Split a normalized line into (artist, title).

    If no clear delimiter is found, returns (None, line).
    Never drops or discards line text.
    """
    clean = line.strip()
    if not clean:
        return None, ""

    # Check for quotes pattern: '"Title" by Artist'
    if clean.startswith('"') or clean.startswith("'"):
        # Match "Title" by Artist
        quote_by_match = re.match(r'^["\']([^"\']+)["\']\s+(?:by|-)\s+(.+)$', clean, re.IGNORECASE)
        if quote_by_match:
            title = quote_by_match.group(1).strip()
            artist = quote_by_match.group(2).strip()
            return artist or None, title

    # Check for dash delimiters first (highest priority in standard tracklists)
    for sep in _DASH_DELIMITERS:
        if sep in clean:
            parts = clean.split(sep, 1)
            artist = parts[0].strip(' "“\'')
            title = parts[1].strip(' "“\'')
            if artist and title:
                return artist, title

    # Check for colon delimiter: e.g. "Queen: Bohemian Rhapsody"
    if ":" in clean:
        parts = clean.split(":", 1)
        artist = parts[0].strip(' "“\'')
        title = parts[1].strip(' "“\'')
        # Only treat colon as delimiter if the left side looks like an artist name (not e.g. http)
        if artist and title and len(artist) <= 50 and not artist.lower().startswith("track"):
            return artist, title

    # Check for " by " separator: e.g. "Bohemian Rhapsody by Queen"
    by_parts = _RE_BY_SEP.split(clean, 1)
    if len(by_parts) == 2:
        title = by_parts[0].strip(' "“\'')
        artist = by_parts[1].strip(' "“\'')
        if artist and title:
            return artist, title

    # No delimiter found: treat whole line as title / free-text query
    return None, clean

