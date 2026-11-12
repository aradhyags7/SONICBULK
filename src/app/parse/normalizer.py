"""String normalization and noise cleaning for parsed song lines."""

from __future__ import annotations

import re

# Leading numbering: "1.", "12)", "#12", "(12)", "03 - ", "12 - "
_RE_NUMBERING = re.compile(
    r"^\s*(?:#?\d+\s*[\.\)\:\-]\s*|\(\d+\)\s*|#\d+\s+)",
    re.IGNORECASE,
)

# Leading bullets: "•", "-", "*", "▪", "▫", "–", "—", ">"
_RE_BULLET = re.compile(
    r"^[\s\u2022\u2023\u25E6\u2043\u2219\*\-\–\—\>\•\▪\▫\~\+\|]+\s*",
    re.UNICODE,
)

# Trailing comments: "  # Duplicate", " // comment"
_RE_COMMENTS = re.compile(r"\s+(?:#|//)\s+.*$")

# Trailing duration: "3:45", "03:45", "1:02:15"
_RE_DURATION = re.compile(
    r"\s*[\(\[]?\b\d{1,2}:\d{2}(?::\d{2})?\b[\)\]]?\s*$",
)

# Trailing BPM: "128 bpm", "120 BPM", "140bpm"
_RE_BPM = re.compile(
    r"\s*[\(\[]?\b\d{2,3}\s*bpm\b[\)\]]?\s*$",
    re.IGNORECASE,
)

# URLs: "http://...", "https://..."
_RE_URL = re.compile(
    r"https?://\S+",
    re.IGNORECASE,
)

# Bracketed noise: (Official Video), [Lyrics], (Audio), (Remastered 2020), etc.
# Longer phrases must come before shorter prefixes
_NOISE_TERMS = (
    r"official\s*(?:music\s*video|lyric\s*video|video|audio|visualizer|clip)"
    r"|lyrics?\s*video|official|visualizer|lyrics?"
    r"|remastered(?:\s*\d{4})?|remaster(?:\s*\d{4})?"
    r"|live(?:\s+at\s+[\w\s]+)?|extended\s*mix|radio\s*edit"
    r"|original\s*mix|full\s*track|audio|hd|4k|hq"
)

_RE_BRACKETED_NOISE = re.compile(
    rf"[\(\[\{{]\s*(?:{_NOISE_TERMS})\s*[\)\]\}}]",
    re.IGNORECASE,
)

# Multiple spaces
_RE_SPACES = re.compile(r"\s+")

# Emojis and miscellaneous symbols (preserve alphanumeric, accented Latin, basic punctuation)
_RE_EMOJI = re.compile(
    r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]",
    flags=re.UNICODE,
)


def normalize_line(line: str) -> str:
    """Clean a raw line by stripping bullets, numbering, durations, URLs, and noise tags."""
    if not line:
        return ""

    # Strip inline comments
    text = _RE_COMMENTS.sub("", line)

    # Remove URLs
    text = _RE_URL.sub(" ", text)

    # Remove emojis
    text = _RE_EMOJI.sub(" ", text)

    # Strip bracketed noise (e.g. (Official Video), [Lyrics])
    text = _RE_BRACKETED_NOISE.sub(" ", text)

    # Strip leading numbering and bullets
    text = _RE_NUMBERING.sub("", text)
    text = _RE_BULLET.sub("", text)

    # Strip trailing duration and BPM
    text = _RE_DURATION.sub("", text)
    text = _RE_BPM.sub("", text)

    # Clean redundant whitespace
    text = _RE_SPACES.sub(" ", text).strip()

    # Strip enclosing unmatched quotes
    if len(text) >= 2 and (
        (text.startswith('"') and text.endswith('"')) or
        (text.startswith("'") and text.endswith("'"))
    ):
        text = text[1:-1].strip()

    return text
