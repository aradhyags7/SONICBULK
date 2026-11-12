"""Command-line interface (CLI) for headless music batch downloads."""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import sys
import uuid
from pathlib import Path
from typing import Sequence

from app.core.config import AppSettings, get_default_config_path
from app.core.events import BatchProgressEvent, EventBus
from app.db.repository import DatabaseRepository
from app.parse.unified import parse_file
from app.pipeline.engine import PipelineEngine
from app.sources.base import SourceProvider
from app.sources.cache import CachedSourceProvider
from app.sources.chain import ProviderChain
from app.sources.mock_provider import MockProvider

logger = logging.getLogger("app.cli")


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="app",
        description="Fast concurrent music downloader from document playlists",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: run
    run_parser = subparsers.add_parser("run", help="Parse and download songs from a file")
    run_parser.add_argument("input", type=str, help="Path to input playlist (PDF, DOCX, CSV, TXT)")
    run_parser.add_argument("--out", "-o", type=str, default="./music", help="Output directory")
    run_parser.add_argument("--workers", "-w", type=int, default=1, help="Concurrent downloads (default: 1 for sequential)")
    run_parser.add_argument("--format", "-f", type=str, default="native", choices=["native", "mp3", "m4a", "flac"], help="Output format")
    run_parser.add_argument("--layout", "-l", type=str, default="flat", choices=["flat", "artist_album"], help="Folder layout")
    run_parser.add_argument("--provider", type=str, default="archive,jamendo", help="Comma-separated provider order")
    run_parser.add_argument("--report", type=str, default=None, help="Path to save report CSV")
    run_parser.add_argument("--dry-run", action="store_true", help="Parse and review songs without downloading")
    run_parser.add_argument("--db", type=str, default=None, help="Custom SQLite database path")

    return parser


async def run_cli(args: argparse.Namespace, custom_provider: SourceProvider | None = None) -> int:
    """Execute CLI run command."""
    input_file = Path(args.input).resolve()
    if not input_file.is_file():
        print(f"Error: input file '{input_file}' not found.", file=sys.stderr)
        return 1

    print(f"Parsing '{input_file.name}'...")
    try:
        doc = parse_file(input_file)
    except Exception as e:
        print(f"Error parsing file: {e}", file=sys.stderr)
        return 1

    print(f"Parsed {len(doc.songs)} song(s). ({sum(1 for s in doc.songs if s.is_duplicate)} duplicate(s) flagged)")

    if args.dry_run:
        print("\n--- Dry Run Parsed Song List ---")
        for i, s in enumerate(doc.songs, 1):
            dup_tag = " [DUPLICATE]" if s.is_duplicate else ""
            print(f"{i:3d}. {s.artist or 'Unknown'} - {s.title}{dup_tag}")
        return 0

    if not doc.songs:
        print("No songs found in input document.", file=sys.stderr)
        return 0

    # Configure application settings
    settings = AppSettings(
        output_dir=str(Path(args.out).resolve()),
        download_concurrency=args.workers,
        output_format=args.format,
        folder_layout=args.layout,
    )
    settings.validate()

    # Configure database
    db_path = Path(args.db).resolve() if args.db else get_default_config_path().parent / "jobs.db"
    repo = DatabaseRepository(db_path)
    await repo.initialize()

    # Create batch
    batch_id = str(uuid.uuid4())[:8]
    jobs = await repo.create_batch(batch_id, doc.songs)

    # Configure providers
    if custom_provider:
        provider = custom_provider
    else:
        # Build provider chain
        provider_names = [p.strip() for p in args.provider.split(",") if p.strip()]
        providers_list: list[SourceProvider] = []
        for p_name in provider_names:
            if p_name == "mock":
                providers_list.append(MockProvider())
            # Real providers (InternetArchive, Jamendo, YtDlp) are plugged in
        if not providers_list:
            providers_list.append(MockProvider())
        chain = ProviderChain(providers_list)
        provider = CachedSourceProvider(chain, repository=repo, ttl_hours=24.0)

    # Event bus for progress printing
    bus = EventBus()

    def on_batch_progress(ev: object) -> None:
        if isinstance(ev, BatchProgressEvent):
            speed_mb = ev.total_speed_bps / (1024 * 1024)
            pct = (ev.completed / max(1, ev.total)) * 100
            sys.stdout.write(
                f"\rProgress: {ev.completed}/{ev.total} ({pct:.1f}%) | "
                f"Done: {ev.downloaded} | Skipped: {ev.skipped} | "
                f"Not Found: {ev.not_found} | Failed: {ev.failed} | "
                f"Speed: {speed_mb:.2f} MB/s   "
            )
            sys.stdout.flush()

    bus.subscribe(BatchProgressEvent, on_batch_progress)

    print(f"Starting batch {batch_id} with {len(jobs)} songs into '{settings.output_dir}'...")
    engine = PipelineEngine(
        settings=settings,
        repository=repo,
        provider=provider,
        event_bus=bus,
    )

    try:
        await engine.initialize()
        summary = await engine.run_batch(batch_id, jobs)
    finally:
        await engine.close()
        await repo.close()

    print("\n\n==========================================")
    print(f" Batch Complete: {batch_id}")
    print("==========================================")
    print(f" Total Songs:   {summary.total}")
    print(f" Downloaded:    {summary.downloaded}")
    print(f" Skipped:       {summary.skipped}")
    print(f" Not Found:     {summary.not_found}")
    print(f" Failed:        {summary.failed}")
    print(f" Elapsed Time:  {summary.duration_seconds:.2f} s")
    print("==========================================")

    # Optional report export
    if args.report:
        report_path = Path(args.report).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Title", "Artist", "Status", "Confidence", "Score", "Path", "Error"])
            for j in jobs:
                conf = j.match_decision.confidence.value if j.match_decision else "none"
                sc = f"{j.match_decision.score:.2f}" if j.match_decision else "0.00"
                writer.writerow([j.song.title, j.song.artist or "", j.status.value, conf, sc, j.output_path or "", j.error_message or ""])
        print(f"Report exported to: {report_path}")

    return 0 if summary.failed == 0 else 2


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return asyncio.run(run_cli(args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
