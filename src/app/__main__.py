"""Main executable entrypoint for desktop GUI or CLI."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on sys.path so 'app.*' imports resolve cleanly
_src_dir = str(Path(__file__).resolve().parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)


def main() -> int:
    # If command line arguments are provided (e.g. `app run ...`), route to CLI
    if len(sys.argv) > 1 and sys.argv[1] in ("run", "--help", "-h"):
        from app.cli.app_cli import main as cli_main
        return cli_main(sys.argv[1:])

    # Otherwise launch PySide6 desktop interface
    from PySide6.QtWidgets import QApplication

    from app.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Music Downloader")
    app.setOrganizationName("MusicDownloader")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

