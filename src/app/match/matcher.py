"""Matching engine classifying confidence tiers and auditing match decisions."""

from __future__ import annotations

import logging

from app.core.models import Candidate, Confidence, MatchDecision, SongEntry
from app.match.scorer import score_candidate

logger = logging.getLogger(__name__)


class MatchEngine:
    """Matches candidate results against song queries using configurable thresholds."""

    def __init__(self, threshold_high: float = 0.85, threshold_low: float = 0.55) -> None:
        self.threshold_high = threshold_high
        self.threshold_low = threshold_low

    def rank_candidates(self, song: SongEntry, candidates: list[Candidate]) -> list[tuple[Candidate, MatchDecision]]:
        """Score and sort all candidates descending by final score."""
        scored: list[tuple[Candidate, MatchDecision]] = []
        for cand in candidates:
            decision = score_candidate(song, cand)
            scored.append((cand, decision))

        # Sort descending by score
        scored.sort(key=lambda item: item[1].score, reverse=True)
        return scored

    def match_song(self, song: SongEntry, candidates: list[Candidate]) -> MatchDecision:
        """Pick best candidate and determine confidence tier.

        - Above threshold_high (>= 0.85): HIGH confidence (auto-accepted)
        - Between threshold_low and threshold_high (0.55 .. 0.85): LOW confidence (accepted but flagged)
        - Below threshold_low (< 0.55): NONE (marked not found)
        """
        if not candidates:
            decision = MatchDecision(
                candidate=None,
                confidence=Confidence.NONE,
                score=0.0,
                title_similarity=0.0,
                artist_similarity=0.0,
                penalty_applied=0.0,
                reason="No candidate results returned by providers",
            )
            logger.info("Match result for '%s': NOT FOUND (no candidates)", song.query)
            return decision

        ranked = self.rank_candidates(song, candidates)
        top_cand, top_decision = ranked[0]
        score = top_decision.score

        if score >= self.threshold_high:
            top_decision.confidence = Confidence.HIGH
            reason = f"High confidence match ({score:.2f} >= {self.threshold_high:.2f}): {top_decision.reason}"
            top_decision.reason = reason
            logger.info("Match result for '%s' -> '%s' [HIGH: %.2f]", song.query, top_cand.title, score)
            return top_decision
        elif score >= self.threshold_low:
            top_decision.confidence = Confidence.LOW
            reason = f"Low confidence match ({score:.2f} in [{self.threshold_low:.2f}, {self.threshold_high:.2f}]): {top_decision.reason}"
            top_decision.reason = reason
            logger.info("Match result for '%s' -> '%s' [LOW: %.2f]", song.query, top_cand.title, score)
            return top_decision
        else:
            reason = f"No candidate met minimum threshold ({score:.2f} < {self.threshold_low:.2f}): {top_decision.reason}"
            decision = MatchDecision(
                candidate=None,
                confidence=Confidence.NONE,
                score=score,
                title_similarity=top_decision.title_similarity,
                artist_similarity=top_decision.artist_similarity,
                penalty_applied=top_decision.penalty_applied,
                reason=reason,
            )
            logger.info("Match result for '%s': NOT FOUND (top candidate score %.2f < %.2f)", song.query, score, self.threshold_low)
            return decision

