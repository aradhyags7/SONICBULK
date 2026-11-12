"""Application configuration settings."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class AppSettings:
    """Configurable application settings."""
    output_dir: str = field(default_factory=lambda: str(Path.home() / "Music" / "MusicDownloader"))
    folder_layout: str = "flat"  # "flat" | "artist_album"
    filename_template: str = "{artist} - {title}"
    output_format: str = "native"  # "native" | "mp3" | "m4a" | "flac"
    search_concurrency: int = 8
    resolve_concurrency: int = 6
    download_concurrency: int = 5  # Range: 1-16
    tag_concurrency: int = 4
    per_host_limit: int = 4
    threshold_high: float = 0.85
    threshold_low: float = 0.55
    providers: list[str] = field(default_factory=lambda: ["ytdlp", "archive", "jamendo", "direct"])
    ytdlp_enabled: bool = True
    jamendo_client_id: str = "a568ee4d"  # Default public developer test client ID
    cache_ttl_hours: int = 24
    max_retries: int = 6
    retry_base_delay: float = 1.0
    retry_cap_delay: float = 60.0
    bandwidth_limit_bps: int = 0  # 0 = unlimited
    prevent_sleep: bool = True
    auto_start: bool = False
    auto_resume_on_startup: bool = False
    min_disk_free_mb: int = 500

    def validate(self) -> None:
        """Validate configuration bounds."""
        self.download_concurrency = max(1, min(16, self.download_concurrency))
        self.search_concurrency = max(1, min(32, self.search_concurrency))
        self.resolve_concurrency = max(1, min(32, self.resolve_concurrency))
        self.tag_concurrency = max(1, min(32, self.tag_concurrency))
        self.per_host_limit = max(1, min(32, self.per_host_limit))
        self.threshold_high = max(0.0, min(1.0, self.threshold_high))
        self.threshold_low = max(0.0, min(self.threshold_high, self.threshold_low))

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> AppSettings:
        import dataclasses
        valid_keys = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        settings = cls(**filtered)  # type: ignore[arg-type]
        settings.validate()
        return settings

    def save_to_file(self, path: Path | str) -> None:
        self.validate()
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        temp_p = p.with_suffix(".tmp")
        with open(temp_p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        temp_p.replace(p)

    @classmethod
    def load_from_file(cls, path: Path | str) -> AppSettings:
        p = Path(path)
        if not p.is_file():
            return cls()
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception:
            return cls()


def get_default_config_path() -> Path:
    """Return default config path in user app directory."""
    app_data = os.environ.get("APPDATA")
    if app_data:
        base = Path(app_data) / "MusicDownloader"
    else:
        base = Path.home() / ".config" / "musicdownloader"
    base.mkdir(parents=True, exist_ok=True)
    return base / "settings.json"
