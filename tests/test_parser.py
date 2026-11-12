"""Unit tests for input parsing, normalization, splitting, and deduplication."""

import time
from pathlib import Path

import pytest

from app.core.models import SongEntry
from app.parse.base import ScannedDocumentError
from app.parse.dedupe import deduplicate_songs
from app.parse.normalizer import normalize_line
from app.parse.splitter import split_artist_title
from app.parse.unified import parse_file, parse_text_input

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestNormalizer:
    def test_strip_numbering(self) -> None:
        assert normalize_line("1. Queen - Bohemian Rhapsody") == "Queen - Bohemian Rhapsody"
        assert normalize_line("12) The Beatles - Hey Jude") == "The Beatles - Hey Jude"
        assert normalize_line("#44 Pink Floyd - Time") == "Pink Floyd - Time"
        assert normalize_line("(01) Nirvana - Lithium") == "Nirvana - Lithium"
        assert normalize_line("03 - Radiohead - Karma Police") == "Radiohead - Karma Police"

    def test_strip_bullets(self) -> None:
        assert normalize_line("• Oasis - Wonderwall") == "Oasis - Wonderwall"
        assert normalize_line("- Blur - Song 2") == "Blur - Song 2"
        assert normalize_line("▪ AC/DC - Thunderstruck") == "AC/DC - Thunderstruck"

    def test_strip_bracketed_noise(self) -> None:
        assert normalize_line("Adele - Hello (Official Video)") == "Adele - Hello"
        assert normalize_line("Queen - Radio Ga Ga [Remastered 2011]") == "Queen - Radio Ga Ga"
        assert normalize_line("Eminem - Stan (Lyrics Video)") == "Eminem - Stan"
        assert normalize_line("Gorillaz - Feel Good Inc. [Visualizer] [HD]") == "Gorillaz - Feel Good Inc."
        assert normalize_line("Coldplay - Yellow (Audio)") == "Coldplay - Yellow"

    def test_strip_durations_and_bpm(self) -> None:
        assert normalize_line("Artist - Song 03:45") == "Artist - Song"
        assert normalize_line("Artist - Song (04:12)") == "Artist - Song"
        assert normalize_line("Artist - Song 128 bpm") == "Artist - Song"
        assert normalize_line("Artist - Song [120 BPM]") == "Artist - Song"

    def test_strip_urls_and_emojis(self) -> None:
        assert normalize_line("Queen - Bohemian Rhapsody https://youtube.com/watch?v=123 🔥🎵") == "Queen - Bohemian Rhapsody"

    def test_preserve_accents(self) -> None:
        assert normalize_line("1. Beyoncé - Halo") == "Beyoncé - Halo"
        assert normalize_line("2. Björk - Army of Me") == "Björk - Army of Me"
        assert normalize_line("3. Sigur Rós - Hoppípolla") == "Sigur Rós - Hoppípolla"


class TestSplitter:
    def test_split_dash_variations(self) -> None:
        assert split_artist_title("Queen - Bohemian Rhapsody") == ("Queen", "Bohemian Rhapsody")
        assert split_artist_title("The Beatles – Hey Jude") == ("The Beatles", "Hey Jude")
        assert split_artist_title("Pink Floyd — Comfortably Numb") == ("Pink Floyd", "Comfortably Numb")

    def test_split_by_keyword(self) -> None:
        assert split_artist_title("Bohemian Rhapsody by Queen") == ("Queen", "Bohemian Rhapsody")
        assert split_artist_title("Imagine by John Lennon") == ("John Lennon", "Imagine")

    def test_split_colon(self) -> None:
        assert split_artist_title("AC/DC: Back in Black") == ("AC/DC", "Back in Black")

    def test_split_quotes(self) -> None:
        assert split_artist_title('"Imagine" by John Lennon') == ("John Lennon", "Imagine")
        assert split_artist_title('Queen - "Bohemian Rhapsody"') == ("Queen", "Bohemian Rhapsody")

    def test_featured_artist(self) -> None:
        artist, title = split_artist_title("Drake feat. Rihanna - Take Care")
        assert artist == "Drake feat. Rihanna"
        assert title == "Take Care"

    def test_fallback_unambiguous(self) -> None:
        artist, title = split_artist_title("Just A Random Song Title")
        assert artist is None
        assert title == "Just A Random Song Title"


class TestDeduplication:
    def test_exact_duplicate(self) -> None:
        s1 = SongEntry(raw_text="Queen - Bohemian Rhapsody", artist="Queen", title="Bohemian Rhapsody")
        s2 = SongEntry(raw_text="Queen - Bohemian Rhapsody", artist="Queen", title="Bohemian Rhapsody")
        songs = deduplicate_songs([s1, s2])
        assert not songs[0].is_duplicate
        assert songs[1].is_duplicate
        assert songs[1].near_duplicate_of == songs[0].id

    def test_near_duplicate(self) -> None:
        s1 = SongEntry(raw_text="Queen - Bohemian Rhapsody", artist="Queen", title="Bohemian Rhapsody")
        s2 = SongEntry(raw_text="Queen - Bohemian Rhapsodie", artist="Queen", title="Bohemian Rhapsodie")
        songs = deduplicate_songs([s1, s2])
        assert not songs[0].is_duplicate
        assert songs[1].near_duplicate_of == songs[0].id


class TestFileParsers:
    def test_parse_text_file(self) -> None:
        doc = parse_file(FIXTURES_DIR / "messy_songs.txt")
        assert len(doc.songs) >= 10
        # Verify deduplication marked duplicate item
        duplicates = [s for s in doc.songs if s.is_duplicate or s.near_duplicate_of]
        assert len(duplicates) >= 2

    def test_parse_csv_file(self) -> None:
        doc = parse_file(FIXTURES_DIR / "songs.csv")
        assert len(doc.songs) == 5
        assert doc.songs[0].artist == "Queen"
        assert doc.songs[0].title == "Bohemian Rhapsody"

    def test_parse_docx_file(self) -> None:
        doc = parse_file(FIXTURES_DIR / "songs.docx")
        assert len(doc.songs) >= 5
        titles = [s.title for s in doc.songs]
        assert any("Bohemian Rhapsody" in t for t in titles)
        assert any("Around the World" in t for t in titles)

    def test_parse_standard_pdf(self) -> None:
        doc = parse_file(FIXTURES_DIR / "standard_songs.pdf")
        assert len(doc.songs) >= 4
        # Verify page number was stripped
        assert not any("Page 1 of 1" in s.raw_text for s in doc.songs)

    def test_parse_two_column_pdf(self) -> None:
        doc = parse_file(FIXTURES_DIR / "two_column_songs.pdf")
        # In a 2-column layout, left column items (Queen, Beatles, Nirvana)
        # must precede right column items (Radiohead, Oasis, Blur)
        titles = [s.title for s in doc.songs]
        assert "Bohemian Rhapsody" in titles[0]
        assert "Let It Be" in titles[1]
        assert "Come As You Are" in titles[2]
        assert "Creep" in titles[3]
        assert "Wonderwall" in titles[4]
        assert "Song 2" in titles[5]

    def test_scanned_pdf_detection(self) -> None:
        with pytest.raises(ScannedDocumentError):
            parse_file(FIXTURES_DIR / "scanned_empty.pdf")

    def test_parse_thousand_lines_speed(self) -> None:
        sample_line = "12. Queen feat. David Bowie - Under Pressure (Remastered 2011) [Official Video] 04:05\n"
        thousand_lines = sample_line * 1000

        start = time.perf_counter()
        doc = parse_text_input(thousand_lines)
        duration = time.perf_counter() - start

        assert len(doc.songs) == 1000
        # 1 original + 999 duplicates
        assert sum(1 for s in doc.songs if s.is_duplicate) == 999
        assert duration < 1.0, f"Parsing 1,000 lines took {duration:.3f}s (threshold < 1.0s)"
