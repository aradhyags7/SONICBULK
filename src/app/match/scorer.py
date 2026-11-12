"""Candidate scoring and penalty calculation using Rapidfuzz."""

from __future__ import annotations

import re

from rapidfuzz import fuzz

from app.core.models import Candidate, Confidence, MatchDecision, SongEntry

# Penalized audio variant tags
PENALTY_KEYWORDS = {
    "cover": 0.35,
    "live": 0.25,
    "remix": 0.30,
    "karaoke": 0.40,
    "instrumental": 0.30,
    "8d": 0.35,
    "slowed": 0.35,
    "reverb": 0.30,
    "sped up": 0.35,
    "speed up": 0.35,
    "nightcore": 0.40,
    "tribute": 0.35,
    "acoustic": 0.20,
}

_WORD_BOUNDARY = re.compile(r"\b[\w\']+\b")


def score_candidate(song: SongEntry, candidate: Candidate) -> MatchDecision:
    """Calculate match score and penalties for a candidate against a SongEntry.

    Rules:
    - Title similarity & artist similarity using Rapidfuzz token_set_ratio.
    - Official / topic / verified bonus (+0.05).
    - Penalties for cover, live, remix, karaoke, 8D, slowed, nightcore, etc.
    - If user query explicitly contains the penalty term, penalty is SKIPPED.
    - Full album (>15 min) or snippet (<45s) penalties.
    """
    user_raw_lower = song.raw_text.lower()
    user_title_lower = song.title.lower()
    user_artist_lower = (song.artist or "").lower()

    cand_title_lower = candidate.title.lower()
    cand_artist_lower = (candidate.artist or "").lower()

    # 1. Title Similarity
    title_sim = fuzz.token_set_ratio(user_title_lower, cand_title_lower) / 100.0

    # 2. Artist Similarity
    if user_artist_lower:
        if cand_artist_lower:
            artist_sim = fuzz.token_set_ratio(user_artist_lower, cand_artist_lower) / 100.0
        else:
            # Check if artist is mentioned in candidate title
            artist_in_title_sim = fuzz.partial_ratio(user_artist_lower, cand_title_lower) / 100.0
            artist_sim = artist_in_title_sim * 0.9
    else:
        # User did not specify artist (free-text query)
        artist_sim = 1.0

    # 3. Base composite score (60% title, 40% artist)
    if user_artist_lower:
        base_score = (0.60 * title_sim) + (0.40 * artist_sim)
    else:
        base_score = title_sim

    # 4. Bonuses: official / topic / verified
    bonus = 0.0
    reasons: list[str] = []
    if candidate.is_official or candidate.is_verified:
        bonus += 0.05
        reasons.append("official/verified bonus (+0.05)")
    if "topic" in cand_artist_lower:
        bonus += 0.03
        reasons.append("topic channel bonus (+0.03)")

    # 5. Penalties for noise terms
    total_penalty = 0.0
    for term, penalty_weight in PENALTY_KEYWORDS.items():
        # Check if term appears in candidate title
        if re.search(rf"\b{re.escape(term)}\b", cand_title_lower):
            # Check if term was in user's original query
            if re.search(rf"\b{re.escape(term)}\b", user_raw_lower):
                # User specifically asked for this term: DO NOT penalize
                reasons.append(f"exempt '{term}' (in user query)")
            else:
                total_penalty += penalty_weight
                reasons.append(f"penalty for '{term}' (-{penalty_weight:.2f})")

    # 6. Duration penalties
    if candidate.duration_seconds is not None:
        dur = candidate.duration_seconds
        if dur > 900:  # > 15 minutes: likely full album or 1-hour loop
            total_penalty += 0.35
            reasons.append("penalty for full-album/hour-loop duration (-0.35)")
        elif dur < 45:  # < 45 seconds: likely ringtone or audio snippet
            total_penalty += 0.35
            reasons.append("penalty for ringtone/short-snippet duration (-0.35)")

    # Calculate final score clamped between 0.0 and 1.0
    final_score = max(0.0, min(1.0, base_score + bonus - total_penalty))
    candidate.score = final_score

    reason_str = f"title={title_sim:.2f}, artist={artist_sim:.2f}"
    if reasons:
        reason_str += f"; {', '.join(reasons)}"

    return MatchDecision(
        candidate=candidate,
        confidence=Confidence.NONE,  # Evaluated by MatchEngine against thresholds
        score=final_score,
        title_similarity=title_sim,
        artist_similarity=artist_sim,
        penalty_applied=total_penalty,
        reason=reason_str,
    )
