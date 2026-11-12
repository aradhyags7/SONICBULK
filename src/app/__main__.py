"""Main executable entrypoint for desktop GUI or CLI."""

from __future__ import annotations

import sys


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

