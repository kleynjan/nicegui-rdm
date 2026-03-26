"""
Event logging infrastructure for RDM debug panel.

Provides a rotating buffer of store events with listener support for live updates.
"""

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

from ..store.notifier import StoreEvent


@dataclass
class EventLogEntry:
    """A logged store event with metadata."""
    timestamp: float
    store_name: str
    tenant: str
    observer_name: str
    topics: dict[str, Any] | None
    event: StoreEvent
    notified: bool = True  # Whether observer was actually notified (topic match)

    @property
    def time_str(self) -> str:
        """Format timestamp as HH:MM:SS.mmm"""
        t = time.localtime(self.timestamp)
        ms = int((self.timestamp % 1) * 1000)
        return f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}.{ms:03d}"


@dataclass
class StoreStats:
    """Aggregated statistics for a store."""
    store_name: str
    tenant: str
    observer_count: int = 0
    event_count: int = 0
    last_event_time: float = 0.0
    observers: list[dict] = field(default_factory=list)  # [{name, topics}]


class EventLog:
    """Global event log with rotating buffer and live update listeners.

    Stores the most recent N events and notifies listeners when new events arrive.
    """

    def __init__(self, max_entries: int = 200):
        self._entries: deque[EventLogEntry] = deque(maxlen=max_entries)
        self._listeners: list[Callable[[EventLogEntry], None]] = []
        self._store_stats: dict[tuple[str, str], StoreStats] = {}  # (tenant, name) -> stats
        self._enabled = False

    def enable(self) -> None:
        """Enable event logging."""
        self._enabled = True

    def disable(self) -> None:
        """Disable event logging."""
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def log(self, entry: EventLogEntry) -> None:
        """Log an event and notify listeners."""
        if not self._enabled:
            return
        self._entries.append(entry)
        self._update_stats(entry)
        for listener in self._listeners:
            try:
                listener(entry)
            except Exception:
                pass  # Don't let listener errors break logging

    def _update_stats(self, entry: EventLogEntry) -> None:
        """Update store statistics from logged event."""
        key = (entry.tenant, entry.store_name)
        if key not in self._store_stats:
            self._store_stats[key] = StoreStats(
                store_name=entry.store_name,
                tenant=entry.tenant
            )
        stats = self._store_stats[key]
        stats.event_count += 1
        stats.last_event_time = entry.timestamp

    def update_observer_info(self, tenant: str, store_name: str, observers: list[dict]) -> None:
        """Update observer list for a store (called on observer add/remove)."""
        key = (tenant, store_name)
        if key not in self._store_stats:
            self._store_stats[key] = StoreStats(store_name=store_name, tenant=tenant)
        stats = self._store_stats[key]
        stats.observers = observers
        stats.observer_count = len(observers)

    def get_entries(self, limit: int | None = None) -> list[EventLogEntry]:
        """Get logged entries, newest first."""
        entries = list(self._entries)
        entries.reverse()
        if limit:
            return entries[:limit]
        return entries

    def get_store_stats(self) -> list[StoreStats]:
        """Get statistics for all stores."""
        return list(self._store_stats.values())

    def clear(self) -> None:
        """Clear all logged entries (keeps stats)."""
        self._entries.clear()

    def add_listener(self, callback: Callable[[EventLogEntry], None]) -> None:
        """Add listener for new events."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[EventLogEntry], None]) -> None:
        """Remove event listener."""
        self._listeners = [l for l in self._listeners if l != callback]


# Global singleton
event_log = EventLog()
