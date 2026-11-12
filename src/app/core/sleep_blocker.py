"""Windows and cross-platform system sleep prevention during active downloads."""

from __future__ import annotations

import ctypes
import logging
import platform

logger = logging.getLogger(__name__)

# Windows Execution State flags
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_AWAYMODE_REQUIRED = 0x00000040


class SleepBlocker:
    """Prevents OS from entering sleep/standby mode during active download batches."""

    def __init__(self) -> None:
        self.is_blocking = False
        self._is_windows = platform.system() == "Windows"

    def enable(self) -> None:
        """Prevent system sleep."""
        if self.is_blocking:
            return
        if self._is_windows:
            try:
                ctypes.windll.kernel32.SetThreadExecutionState(
                    ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
                )
                self.is_blocking = True
                logger.info("System sleep prevention enabled (SetThreadExecutionState)")
            except Exception as e:
                logger.warning("Failed to set thread execution state: %s", e)
        else:
            self.is_blocking = True

    def disable(self) -> None:
        """Restore normal system sleep behavior."""
        if not self.is_blocking:
            return
        if self._is_windows:
            try:
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
                self.is_blocking = False
                logger.info("System sleep prevention disabled")
            except Exception as e:
                logger.warning("Failed to reset thread execution state: %s", e)
        else:
            self.is_blocking = False
