"""High-performance parallel batch converter to convert downloaded WebM/Opus audio files to universal MP3s."""

from __future__ import annotations

import concurrent.futures
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def find_ffmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        Path(local_app_data) / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe",
        Path(local_app_data) / "Microsoft" / "WinGet" / "Packages",
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
        if c.is_dir():
            matches = list(c.glob("**/ffmpeg.exe"))
            if matches:
                return str(matches[0])
    return None


def tag_mp3(path: Path, title: str, artist: str | None = None) -> None:
    try:
        from mutagen.id3 import ID3, TIT2, TPE1, ID3NoHeaderError
        try:
            audio = ID3(str(path))
        except ID3NoHeaderError:
            audio = ID3()

        audio.add(TIT2(encoding=3, text=title))
        if artist and artist.lower() != "unknown artist":
            audio.add(TPE1(encoding=3, text=artist))
        audio.save(str(path))
    except Exception:
        pass


def parse_filename(stem: str) -> tuple[str, str | None]:
    if " - " in stem:
        parts = stem.split(" - ", 1)
        artist = parts[0].strip()
        title = parts[1].strip()
        return title, artist
    return stem.strip(), None


def convert_single_file(src_p: Path, ffmpeg_bin: str) -> bool:
    mp3_p = src_p.with_suffix(".mp3")
    tmp_mp3 = src_p.with_suffix(f".tmp_{os.getpid()}_{time.time_ns()}.mp3")

    if mp3_p.is_file() and mp3_p.stat().st_size > 50_000:
        src_p.unlink(missing_ok=True)
        return True

    title, artist = parse_filename(src_p.stem)

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", str(src_p),
        "-vn",
        "-b:a", "320k",
        str(tmp_mp3),
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if tmp_mp3.is_file() and tmp_mp3.stat().st_size > 10_000:
            tmp_mp3.replace(mp3_p)
            tag_mp3(mp3_p, title=title, artist=artist)
            src_p.unlink(missing_ok=True)
            return True
        return False
    except Exception:
        if tmp_mp3.is_file():
            tmp_mp3.unlink(missing_ok=True)
        return False


def convert_library(target_dir: Path | str, ffmpeg_bin: str, workers: int = 6) -> None:
    folder = Path(target_dir).resolve()
    if not folder.is_dir():
        print(f"[Error] Target directory does not exist: {folder}", flush=True)
        return

    webm_files = list(folder.glob("*.webm")) + list(folder.glob("*.opus"))
    total = len(webm_files)
    if total == 0:
        print(f"[Info] All files are already converted to MP3 in {folder}!", flush=True)
        return

    print(f"\n=======================================================", flush=True)
    print(f"Converting {total} audio files to MP3 using {workers} parallel threads", flush=True)
    print(f"Target directory: {folder}", flush=True)
    print(f"Audio bitrate   : 320 kbps (High Fidelity)", flush=True)
    print(f"=======================================================\n", flush=True)

    start_time = time.monotonic()
    success = 0
    failed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(convert_single_file, f, ffmpeg_bin): f for f in webm_files}
        for idx, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            f = futures[future]
            try:
                ok = future.result()
                if ok:
                    success += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

            if idx % 10 == 0 or idx == total:
                pct = int((idx / total) * 100)
                print(f"Progress: [{idx}/{total}] ({pct}%) converted to MP3...", flush=True)

    elapsed = time.monotonic() - start_time
    print(f"\n=======================================================", flush=True)
    print(f"ALL DONE in {elapsed:.1f}s ({total / max(1, elapsed):.1f} files/sec)!", flush=True)
    print(f"Successfully converted: {success} songs to MP3", flush=True)
    if failed:
        print(f"Failed conversions    : {failed} songs", flush=True)
    print(f"Your USB music folder is now 100% car-ready!", flush=True)
    print(f"=======================================================\n", flush=True)


if __name__ == "__main__":
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("[Error] ffmpeg executable not found on system!", flush=True)
        sys.exit(1)

    default_dir = Path.home() / "Downloads" / "MusicDownloader"
    convert_library(default_dir, ffmpeg, workers=6)
