"""Disk space utilities."""

from __future__ import annotations

import shutil
from pathlib import Path


class DiskFullError(Exception):
    """Raised when available disk space is below required threshold."""


def check_disk_space(target_dir: Path | str, min_free_mb: int = 500) -> tuple[bool, int]:
    """Check if free disk space is at least min_free_mb.

    Returns (is_sufficient, free_mb).
    """
    path = Path(target_dir).resolve()
    # Find existing parent directory if target_dir doesn't exist yet
    while not path.exists() and path.parent != path:
        path = path.parent

    try:
        usage = shutil.disk_usage(str(path))
        free_mb = usage.free // (1024 * 1024)
        return free_mb >= min_free_mb, free_mb
    except Exception:
        # If unable to determine, assume sufficient
        return True, 999999
