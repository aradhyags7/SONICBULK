"""File and directory path generation, template rendering, and filename sanitization."""

from __future__ import annotations

import re
from pathlib import Path

# Characters forbidden in filenames across Windows, macOS, and Linux
_INVALID_CHARS = re.compile(r'[\\/*?:"<>|]')

# Windows reserved device names
_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def sanitize_filename(name: str, max_length: int = 120) -> str:
    """Sanitize a filename component by stripping invalid characters and reserved words."""
    if not name:
        return "Unknown"

    # Replace forbidden characters with hyphen
    cleaned = _INVALID_CHARS.sub("-", name)

    # Strip control characters
    cleaned = "".join(ch for ch in cleaned if ord(ch) >= 32)

    # Clean multiple spaces/hyphens
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned)

    # Strip trailing periods and whitespace (critical on Windows)
    cleaned = cleaned.strip(". ")

    # Check for reserved Windows device names
    base_upper = cleaned.upper().split(".")[0]
    if base_upper in _RESERVED_NAMES:
        cleaned = f"_{cleaned}"

    if not cleaned:
        cleaned = "Unknown"

    # Truncate to max_length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip(". ")

    return cleaned


def resolve_collision_path(target_path: Path) -> Path:
    """If target_path already exists and has different contents, return a numbered suffix path."""
    if not target_path.exists():
        return target_path

    parent = target_path.parent
    stem = target_path.stem
    ext = target_path.suffix

    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){ext}"
        if not candidate.exists():
            return candidate
        counter += 1


def generate_output_path(
    output_dir: Path | str,
    layout: str,
    template: str,
    title: str,
    artist: str | None = None,
    album: str | None = None,
    extension: str = "mp3",
) -> Path:
    """Render folder layout and filename template with full sanitization."""
    out_dir = Path(output_dir).resolve()

    clean_artist = sanitize_filename(artist or "Unknown Artist")
    clean_title = sanitize_filename(title or "Unknown Title")
    clean_album = sanitize_filename(album or "Unknown Album")
    clean_ext = extension.lstrip(".").lower() or "mp3"

    # Folder layout: "flat" or "artist_album"
    if layout == "artist_album":
        folder = out_dir / clean_artist / clean_album
    else:
        folder = out_dir

    # Render filename template
    rendered = template.format(
        artist=clean_artist,
        title=clean_title,
        album=clean_album,
    )
    sanitized_name = f"{sanitize_filename(rendered)}.{clean_ext}"

    # Verify total path length < 255 chars
    full_path = folder / sanitized_name
    if len(str(full_path)) > 250:
        # Truncate title component to fit under MAX_PATH limit
        excess = len(str(full_path)) - 245
        truncated_title = sanitize_filename(clean_title[: max(10, len(clean_title) - excess)])
        rendered = template.format(artist=clean_artist, title=truncated_title, album=clean_album)
        sanitized_name = f"{sanitize_filename(rendered)}.{clean_ext}"
        full_path = folder / sanitized_name

    return full_path

