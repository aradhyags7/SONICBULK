"""Matching package for candidate scoring and confidence ranking."""

from app.match.matcher import MatchEngine
from app.match.scorer import PENALTY_KEYWORDS, score_candidate

__all__ = ["MatchEngine", "score_candidate", "PENALTY_KEYWORDS"]
