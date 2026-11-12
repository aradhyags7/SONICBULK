"""Optional audio format conversion using ffmpeg."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def is_ffmpeg_available() -> bool:
    """Check if ffmpeg executable is present in PATH."""
    return shutil.which("ffmpeg") is not None


def convert_audio_file(src_path: Path | str, target_format: str = "native") -> Path:
    """Convert audio file to target format if requested and ffmpeg is available.

    If target_format is 'native' or matches the current extension, no re-encode is performed.
    """
    path = Path(src_path).resolve()
    clean_target = target_format.lower().lstrip(".")

    if clean_target in ("native", "", path.suffix.lstrip(".").lower()):
        return path

    if not is_ffmpeg_available():
        logger.info("ffmpeg not found in PATH; keeping native format for '%s'", path.name)
        return path

    target_path = path.with_suffix(f".{clean_target}")
    tmp_target = path.with_suffix(f".conv_tmp.{clean_target}")

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(path),
        "-vn",
        "-b:a", "256k",
        str(tmp_target),
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        if tmp_target.is_file() and tmp_target.stat().st_size > 0:
            path.unlink(missing_ok=True)
            tmp_target.replace(target_path)
            return target_path
        return path
    except Exception as e:
        logger.warning("ffmpeg conversion failed for '%s' (%s); keeping native format", path.name, e)
        if tmp_target.is_file():
            tmp_target.unlink(missing_ok=True)
        return path
