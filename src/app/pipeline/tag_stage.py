"""Audio metadata tagger using Mutagen for MP3, M4A, FLAC, and OGG."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def tag_audio_file(
    file_path: Path | str,
    title: str,
    artist: str | None = None,
    album: str | None = None,
    cover_bytes: bytes | None = None,
) -> bool:
    """Write metadata tags into audio file without re-encoding."""
    path = Path(file_path).resolve()
    if not path.is_file():
        logger.warning("Cannot tag non-existent file: %s", path)
        return False

    ext = path.suffix.lower()
    try:
        if ext == ".mp3":
            _tag_mp3(path, title=title, artist=artist, album=album, cover_bytes=cover_bytes)
        elif ext in (".m4a", ".mp4", ".aac"):
            _tag_m4a(path, title=title, artist=artist, album=album, cover_bytes=cover_bytes)
        elif ext == ".flac":
            _tag_flac(path, title=title, artist=artist, album=album, cover_bytes=cover_bytes)
        elif ext in (".ogg", ".opus"):
            _tag_ogg(path, title=title, artist=artist, album=album)
        else:
            logger.debug("Untagged format: %s", ext)
        return True

    except Exception as e:
        logger.warning("Tagging failed for '%s': %s", path.name, e)
        return False


def _tag_mp3(path: Path, title: str, artist: str | None, album: str | None, cover_bytes: bytes | None) -> None:
    from mutagen.id3 import APIC, ID3, TALB, TIT2, TPE1, ID3NoHeaderError

    try:
        audio = ID3(str(path))
    except ID3NoHeaderError:
        audio = ID3()

    audio.add(TIT2(encoding=3, text=title))
    if artist:
        audio.add(TPE1(encoding=3, text=artist))
    if album:
        audio.add(TALB(encoding=3, text=album))
    if cover_bytes:
        audio.add(APIC(
            encoding=3,
            mime="image/jpeg" if cover_bytes.startswith(b"\xff\xd8") else "image/png",
            type=3,  # Front cover
            desc="Cover",
            data=cover_bytes,
        ))
    audio.save(str(path))


def _tag_m4a(path: Path, title: str, artist: str | None, album: str | None, cover_bytes: bytes | None) -> None:
    from mutagen.mp4 import MP4, MP4Cover

    audio = MP4(str(path))
    audio["\xa9nam"] = [title]
    if artist:
        audio["\xa9ART"] = [artist]
    if album:
        audio["\xa9alb"] = [album]
    if cover_bytes:
        fmt = MP4Cover.FORMAT_JPEG if cover_bytes.startswith(b"\xff\xd8") else MP4Cover.FORMAT_PNG
        audio["covr"] = [MP4Cover(cover_bytes, imageformat=fmt)]
    audio.save()


def _tag_flac(path: Path, title: str, artist: str | None, album: str | None, cover_bytes: bytes | None) -> None:
    from mutagen.flac import FLAC, Picture

    audio = FLAC(str(path))
    audio["title"] = title
    if artist:
        audio["artist"] = artist
    if album:
        audio["album"] = album
    if cover_bytes:
        pic = Picture()
        pic.type = 3
        pic.mime = "image/jpeg" if cover_bytes.startswith(b"\xff\xd8") else "image/png"
        pic.data = cover_bytes
        audio.clear_pictures()
        audio.add_picture(pic)
    audio.save()


def _tag_ogg(path: Path, title: str, artist: str | None, album: str | None) -> None:
    from mutagen.oggvorbis import OggVorbis

    audio = OggVorbis(str(path))
    audio["title"] = title
    if artist:
        audio["artist"] = artist
    if album:
        audio["album"] = album
    audio.save()

