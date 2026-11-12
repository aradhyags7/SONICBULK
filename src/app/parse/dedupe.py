"""Deduplication and near-duplicate detection for parsed song lists."""

from __future__ import annotations

import collections
import re

from rapidfuzz import fuzz

from app.core.models import SongEntry

_NORM_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def canonical_key(artist: str | None, title: str) -> str:
    """Produce normalized canonical string key for exact duplicate matching."""
    norm_artist = _NORM_PUNCT.sub("", (artist or "").lower()).strip()
    norm_title = _NORM_PUNCT.sub("", title.lower()).strip()
    norm_artist = " ".join(norm_artist.split())
    norm_title = " ".join(norm_title.split())
    return f"{norm_artist}:::{norm_title}"


def deduplicate_songs(songs: list[SongEntry], near_threshold: float = 88.0) -> list[SongEntry]:
    """Flag exact duplicates and near-duplicates in a list of songs.

    Preserves original order. Parsing 1,000 items takes <0.1 s.
    """
    seen_exact: dict[str, SongEntry] = {}
    title_buckets: dict[str, list[SongEntry]] = collections.defaultdict(list)

    for song in songs:
        key = canonical_key(song.artist, song.title)
        if key in seen_exact:
            song.is_duplicate = True
            song.near_duplicate_of = seen_exact[key].id
            continue

        seen_exact[key] = song

        # Near-duplicate check: search against candidate bucket
        title_norm = _NORM_PUNCT.sub("", song.title.lower()).strip()
        first_token = title_norm.split()[0] if title_norm else ""
        bucket_candidates = title_buckets.get(first_token, [])

        for prev in bucket_candidates:
            # Check title similarity
            score = fuzz.token_sort_ratio(song.title.lower(), prev.title.lower())
            if score >= near_threshold:
                # If artist is present on both, ensure artists match closely too
                if song.artist and prev.artist:
                    artist_score = fuzz.token_sort_ratio(song.artist.lower(), prev.artist.lower())
                    if artist_score < 75:
                        continue
                song.near_duplicate_of = prev.id
                break

        if first_token:
            title_buckets[first_token].append(song)

    return songs
