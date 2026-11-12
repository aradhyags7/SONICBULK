"""Event models and dispatcher for pipeline-to-UI communication."""

from __future__ import annotations

import collections
from dataclasses import dataclass
from typing import Callable

from app.core.models import JobStatus


@dataclass(slots=True)
class JobProgressEvent:
    job_id: str
    bytes_downloaded: int
    total_bytes: int | None
    speed_bps: float


@dataclass(slots=True)
class JobStatusEvent:
    job_id: str
    status: JobStatus
    error_message: str | None = None
    output_path: str | None = None


@dataclass(slots=True)
class BatchProgressEvent:
    batch_id: str
    total: int
    completed: int
    downloaded: int
    skipped: int
    not_found: int
    failed: int
    active_downloads: int
    total_speed_bps: float


EventCallback = Callable[[object], None]


class EventBus:
    """Thread-safe event dispatcher for core events."""

    def __init__(self) -> None:
        self._subscribers: dict[type, list[EventCallback]] = collections.defaultdict(list)

    def subscribe(self, event_type: type, callback: EventCallback) -> None:
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: type, callback: EventCallback) -> None:
        if event_type in self._subscribers and callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    def publish(self, event: object) -> None:
        for callback in list(self._subscribers.get(type(event), [])):
            try:
                callback(event)
            except Exception:
                pass
