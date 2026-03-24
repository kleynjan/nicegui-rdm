"""
Event notification with batching and debouncing support.

EventNotifier manages observer notifications for Store, providing:
- Immediate notifications (debounce_ms=0)
- Time-based debouncing to coalesce rapid events
- Explicit batching via context manager
"""

import asyncio
import inspect
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class StoreEvent:
    """Store events / notifications, sent to store observers"""
    verb: str  # "create" | "update" | "delete" | "batch"
    item: dict  # For single ops: the item. For batch: metadata


class EventNotifier:
    """Manages observer notifications with optional batching and debouncing.

    Extracted from Store to keep the base class simple.

    Args:
        debounce_ms: Milliseconds to wait for quiet period before flushing.
                     0 = disabled (immediate notifications)
    """

    def __init__(self, debounce_ms: int = 0):
        self._observers: list[Callable[[StoreEvent], Any]] = []
        self._debounce_ms = debounce_ms
        self._batch_depth = 0
        self._pending_events: list[StoreEvent] = []
        self._last_event_time = 0.0
        self._flush_task: asyncio.Task | None = None

    def add_observer(self, observer: Callable[[StoreEvent], Any]) -> None:
        """Add an observer to receive store events"""
        self._observers.append(observer)

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

    async def _flush_events(self) -> None:
        """Fire events to all observers."""
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

        for observer in self._observers:
            if inspect.iscoroutinefunction(observer):
                await observer(event_to_fire)
            else:
                observer(event_to_fire)
