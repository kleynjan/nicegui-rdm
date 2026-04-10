"""
Event notification with batching and debouncing support.

EventNotifier manages observer notifications for Store, providing:
- Immediate notifications (debounce_ms=0)
- Time-based debouncing to coalesce rapid events
- Explicit batching via context manager
"""

from __future__ import annotations

import asyncio
import inspect
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ..debug.event_log import EventLog


@dataclass
class StoreEvent:
    """Store events / notifications, sent to store observers"""
    verb: str  # "create" | "update" | "delete" | "batch"
    item: dict  # For single ops: the item. For batch: metadata


@dataclass
class ObserverEntry:
    """Observer registration with optional topic filter."""
    callback: Callable[[StoreEvent], Any]
    topics: dict[str, Any] | None = None  # None = wildcard (all events)
    name: str = ""  # Derived from callback inspection


def _infer_observer_name(callback: Callable) -> str:
    """Infer a human-readable name from a callback function or method."""
    # Method on object: "DataTable#a3f2" (class + short id)
    if hasattr(callback, '__self__'):
        obj = callback.__self__
        class_name = obj.__class__.__name__
        short_id = hex(id(obj))[-4:]
        return f"{class_name}#{short_id}"
    # Plain function: use __name__
    if hasattr(callback, '__name__'):
        return callback.__name__
    return f"observer#{hex(id(callback))[-4:]}"


class EventNotifier:
    """Manages observer notifications with optional batching and debouncing.

    Supports topic-based filtering: observers can subscribe to specific
    field values (e.g., topics={"role_id": 5}) to receive only relevant events.

    Args:
        debounce_ms: Milliseconds to wait for quiet period before flushing.
                     0 = disabled (immediate notifications)
    """

    def __init__(self, debounce_ms: int = 0):
        self._observers: list[ObserverEntry] = []
        self._topic_fields: list[str] = []
        self._debounce_ms = debounce_ms
        self._batch_depth = 0
        self._pending_events: list[StoreEvent] = []
        self._last_event_time = 0.0
        self._flush_task: asyncio.Task | None = None
        self._event_log: EventLog | None = None
        self._store_name: str = ""
        self._store_tenant: str = ""

    def set_topic_fields(self, fields: list[str]) -> None:
        """Configure which item fields can be used for topic-based routing."""
        self._topic_fields = fields

    def set_event_log(self, event_log: EventLog, store_name: str, tenant: str = "") -> None:
        """Set the event log for debug tracking."""
        self._event_log = event_log
        self._store_name = store_name
        self._store_tenant = tenant

    def add_observer(self, observer: Callable[[StoreEvent], Any], topics: dict[str, Any] | None = None) -> None:
        """Add observer with optional topic subscription."""
        name = _infer_observer_name(observer)
        self._observers.append(ObserverEntry(callback=observer, topics=topics, name=name))

    def remove_observer(self, observer: Callable[[StoreEvent], Any]) -> None:
        """Remove observer by callback identity."""
        self._observers = [e for e in self._observers if e.callback != observer]

    @property
    def observer_count(self) -> int:
        """Get the number of observers"""
        return len(self._observers)

    async def notify(self, event: StoreEvent) -> None:
        """Queue event and fire to observers (with batching/debouncing if configured)."""
        self._pending_events.append(event)
        self._last_event_time = time.monotonic()

        if self._batch_depth > 0:
            return  # Inside batch context - wait for exit

        if self._debounce_ms > 0:
            await self._schedule_debounced_flush()
        else:
            await self._flush_events()

    async def _schedule_debounced_flush(self) -> None:
        """Start debounce loop if not already running."""
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._debounce_loop())

    async def _debounce_loop(self) -> None:
        """Wait until no new events arrive within the debounce window."""
        delay = self._debounce_ms / 1000
        while True:
            await asyncio.sleep(delay)
            elapsed = time.monotonic() - self._last_event_time
            if elapsed >= delay:
                # Quiet period reached - flush and exit
                await self._flush_events()
                return
            # New events arrived during sleep - loop again

    @asynccontextmanager
    async def batch(self):
        """Context manager for explicit batching.

        All events within the context are collected and fired as a single
        batch event on exit. Bypasses debouncing for immediate flush.

        Usage:
            async with notifier.batch():
                await notifier.notify(event1)
                await notifier.notify(event2)
            # Single batch event fires here
        """
        self._batch_depth += 1
        try:
            yield
        finally:
            self._batch_depth -= 1
            if self._batch_depth == 0:
                # Cancel any pending debounce - batch exit is immediate
                if self._flush_task and not self._flush_task.done():
                    self._flush_task.cancel()
                    try:
                        await self._flush_task
                    except asyncio.CancelledError:
                        pass
                    self._flush_task = None
                await self._flush_events()

    def _should_notify(self, event: StoreEvent, topics: dict[str, Any] | None) -> bool:
        """Determine if observer should receive this event."""
        if topics is None:
            return True  # Wildcard - receives all
        if event.verb == "batch":
            return True  # Conservative - batch notifies all
        return all(event.item.get(k) == v for k, v in topics.items())

    async def _flush_events(self) -> None:
        """Fire events to observers, filtered by topic subscriptions."""
        if not self._pending_events:
            return

        events = self._pending_events
        self._pending_events = []

        # Coalesce multiple events into a batch event
        if len(events) == 1:
            event_to_fire = events[0]
        else:
            event_to_fire = StoreEvent(
                verb="batch",
                item={"count": len(events), "verbs": list({e.verb for e in events})}
            )

        for entry in self._observers:
            notified = self._should_notify(event_to_fire, entry.topics)
            # Log to debug event log if enabled
            if self._event_log and self._event_log.is_enabled:
                from ..debug.event_log import EventLogEntry
                self._event_log.log(EventLogEntry(
                    timestamp=time.time(),
                    store_name=self._store_name,
                    tenant=self._store_tenant,
                    observer_name=entry.name,
                    topics=entry.topics,
                    event=event_to_fire,
                    notified=notified,
                ))
            if notified:
                if inspect.iscoroutinefunction(entry.callback):
                    await entry.callback(event_to_fire)
                else:
                    entry.callback(event_to_fire)
