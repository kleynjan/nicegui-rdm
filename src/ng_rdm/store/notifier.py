"""
Event notification with batching and throttling support.

EventNotifier manages observer notifications for Store, providing:
- Immediate notifications (throttle_ms=0)
- Leading+trailing throttling to bound flush frequency under sustained load
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
        obj = getattr(callback, '__self__')
        class_name = obj.__class__.__name__
        short_id = hex(id(obj))[-4:]
        return f"{class_name}#{short_id}"
    # Plain function: use __name__
    if hasattr(callback, '__name__'):
        return callback.__name__
    return f"observer#{hex(id(callback))[-4:]}"


class EventNotifier:
    """Manages observer notifications with optional batching and throttling.

    Supports topic-based filtering: observers can subscribe to specific
    field values (e.g., topics={"role_id": 5}) to receive only relevant events.

    Args:
        throttle_ms: Minimum interval between flushes. Events flush immediately on
                     the leading edge, then at most once per interval while events
                     keep arriving, with a guaranteed trailing flush after the last
                     event. 0 = disabled (immediate notifications). Unlike a pure
                     trailing timer, a sustained sub-interval stream never starves.
    """

    def __init__(self, throttle_ms: int = 0):
        self._observers: list[ObserverEntry] = []
        self._topic_fields: list[str] = []
        self._throttle_ms = throttle_ms
        self._batch_depth = 0
        self._pending_events: list[StoreEvent] = []
        self._last_flush_time = 0.0
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
        """Queue event and fire to observers (with batching/throttling if configured)."""
        self._pending_events.append(event)

        if self._batch_depth > 0:
            return  # Inside batch context - wait for exit

        if self._throttle_ms > 0:
            await self._schedule_throttled_flush()
        else:
            await self._flush_events()

    async def _schedule_throttled_flush(self) -> None:
        """Flush on the leading edge, else coalesce into one trailing flush per interval."""
        interval = self._throttle_ms / 1000
        elapsed = time.monotonic() - self._last_flush_time
        if elapsed >= interval:
            # Leading edge - been quiet at least one interval, flush now
            await self._flush_and_stamp()
        elif self._flush_task is None or self._flush_task.done():
            # Within the interval - schedule a single trailing flush at the boundary
            self._flush_task = asyncio.create_task(self._trailing_flush(interval - elapsed))

    async def _trailing_flush(self, wait: float) -> None:
        """Wait out the remainder of the interval, then flush coalesced events."""
        await asyncio.sleep(wait)
        await self._flush_and_stamp()

    async def _flush_and_stamp(self) -> None:
        """Record the flush time (throttle boundary) and fire pending events."""
        self._last_flush_time = time.monotonic()
        await self._flush_events()

    @asynccontextmanager
    async def batch(self):
        """Context manager for explicit batching.

        All events within the context are collected and fired as a single
        batch event on exit. Bypasses throttling for immediate flush.

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
                # Cancel any pending trailing flush - batch exit is immediate
                if self._flush_task and not self._flush_task.done():
                    self._flush_task.cancel()
                    try:
                        await self._flush_task
                    except asyncio.CancelledError:
                        pass
                    self._flush_task = None
                await self._flush_and_stamp()

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
