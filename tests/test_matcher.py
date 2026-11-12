"""Unit tests for the matching engine, candidate scoring, and noise penalties."""

from app.core.models import Candidate, Confidence, SongEntry
from app.match.matcher import MatchEngine
from app.match.scorer import score_candidate


class TestScorer:
    def test_exact_match_score(self) -> None:
        song = SongEntry(raw_text="Queen - Bohemian Rhapsody", artist="Queen", title="Bohemian Rhapsody")
        cand = Candidate(
            provider="mock",
            source_id="1",
            title="Bohemian Rhapsody",
            artist="Queen",
            duration_seconds=355.0,
            is_official=True,
        )
        decision = score_candidate(song, cand)
        assert decision.score >= 0.95
        assert decision.penalty_applied == 0.0

    def test_penalize_cover_live_remix(self) -> None:
        song = SongEntry(raw_text="Queen - Bohemian Rhapsody", artist="Queen", title="Bohemian Rhapsody")
        cand_cover = Candidate(
            provider="mock",
            source_id="2",
            title="Bohemian Rhapsody (Acoustic Cover)",
            artist="Cover Band",
            duration_seconds=300.0,
        )
        decision = score_candidate(song, cand_cover)
        assert decision.penalty_applied >= 0.35
        assert decision.score < 0.70

    def test_skip_penalty_when_user_requested_term(self) -> None:
        # User explicitly asked for "Live"
        song = SongEntry(raw_text="Queen - Bohemian Rhapsody (Live at Wembley)", artist="Queen", title="Bohemian Rhapsody (Live at Wembley)")
        cand_live = Candidate(
            provider="mock",
            source_id="3",
            title="Bohemian Rhapsody (Live at Wembley)",
            artist="Queen",
            duration_seconds=360.0,
            is_official=True,
        )
        decision = score_candidate(song, cand_live)
        # Should NOT apply penalty for 'live' because user requested it
        assert "penalty for 'live'" not in decision.reason
        assert decision.score >= 0.85

    def test_duration_penalties(self) -> None:
        song = SongEntry(raw_text="Led Zeppelin - Stairway to Heaven", artist="Led Zeppelin", title="Stairway to Heaven")
        # Full album / 1-hour loop
        cand_long = Candidate(
            provider="mock",
            source_id="4",
            title="Stairway to Heaven (1 Hour Loop)",
            artist="Led Zeppelin",
            duration_seconds=3600.0,
        )
        decision_long = score_candidate(song, cand_long)
        assert "penalty for full-album" in decision_long.reason

        # Ringtone
        cand_short = Candidate(
            provider="mock",
            source_id="5",
            title="Stairway to Heaven",
            artist="Led Zeppelin",
            duration_seconds=25.0,
        )
        decision_short = score_candidate(song, cand_short)
        assert "penalty for ringtone" in decision_short.reason


class TestMatchEngine:
    def test_high_confidence_auto_accept(self) -> None:
        engine = MatchEngine(threshold_high=0.85, threshold_low=0.55)
        song = SongEntry(raw_text="Nirvana - Smells Like Teen Spirit", artist="Nirvana", title="Smells Like Teen Spirit")
        candidates = [
            Candidate(provider="mock", source_id="1", title="Smells Like Teen Spirit", artist="Nirvana", is_official=True, duration_seconds=301.0),
            Candidate(provider="mock", source_id="2", title="Smells Like Teen Spirit (Cover)", artist="Other", duration_seconds=290.0),
        ]
        decision = engine.match_song(song, candidates)
        assert decision.confidence == Confidence.HIGH
        assert decision.candidate is not None
        assert decision.candidate.source_id == "1"

    def test_low_confidence_flagged(self) -> None:
        engine = MatchEngine(threshold_high=0.85, threshold_low=0.55)
        song = SongEntry(raw_text="Nirvana - Smells Like Teen Spirit", artist="Nirvana", title="Smells Like Teen Spirit")
        # Mediocre match (e.g. artist slightly off and cover)
        candidates = [
            Candidate(provider="mock", source_id="10", title="Teen Spirit Tribute", artist="Nirvana Tribute", duration_seconds=295.0),
        ]
        decision = engine.match_song(song, candidates)
        # Should be classified as LOW confidence or NONE depending on score
        if decision.score >= 0.55:
            assert decision.confidence == Confidence.LOW
            assert decision.candidate is not None

    def test_not_found_below_threshold(self) -> None:
        engine = MatchEngine(threshold_high=0.85, threshold_low=0.55)
        song = SongEntry(raw_text="Queen - Bohemian Rhapsody", artist="Queen", title="Bohemian Rhapsody")
        candidates = [
            Candidate(provider="mock", source_id="99", title="Completely Unrelated Track", artist="Random Person", duration_seconds=180.0),
        ]
        decision = engine.match_song(song, candidates)
        assert decision.confidence == Confidence.NONE
        assert decision.candidate is None
        assert "minimum threshold" in decision.reason
