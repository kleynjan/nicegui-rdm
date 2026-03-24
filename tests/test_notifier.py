"""
Tests for EventNotifier: notification, debouncing, batching.
"""
import asyncio
import pytest
from ng_rdm.store import EventNotifier, StoreEvent


@pytest.fixture
def notifier():
    """A fresh EventNotifier with no debouncing"""
    return EventNotifier(debounce_ms=0)


@pytest.fixture
def debounced_notifier():
    """EventNotifier with 50ms debounce"""
    return EventNotifier(debounce_ms=50)


# --- Basic Notification ---


async def test_notify_single_event(notifier):
    """Single event is delivered immediately"""
    events = []
    notifier.add_observer(lambda e: events.append(e))

    await notifier.notify(StoreEvent(verb="create", item={"id": 1}))

    assert len(events) == 1
    assert events[0].verb == "create"


async def test_notify_multiple_observers(notifier):
    """Multiple observers all receive events"""
    events_a, events_b = [], []
    notifier.add_observer(lambda e: events_a.append(e))
    notifier.add_observer(lambda e: events_b.append(e))

    await notifier.notify(StoreEvent(verb="create", item={"id": 1}))

    assert len(events_a) == 1
    assert len(events_b) == 1


async def test_notify_async_observer(notifier):
    """Async observers are awaited correctly"""
    events = []

    async def async_observer(event):
        events.append(event)

    notifier.add_observer(async_observer)
    await notifier.notify(StoreEvent(verb="create", item={"id": 1}))

    assert len(events) == 1


async def test_observer_count(notifier):
    """observer_count property tracks registered observers"""
    assert notifier.observer_count == 0
    notifier.add_observer(lambda e: None)
    assert notifier.observer_count == 1
    notifier.add_observer(lambda e: None)
    assert notifier.observer_count == 2


# --- Batching ---


async def test_batch_coalesces_events(notifier):
    """Events within batch context are coalesced"""
    events = []
    notifier.add_observer(lambda e: events.append(e))

    async with notifier.batch():
        await notifier.notify(StoreEvent(verb="create", item={"id": 1}))
        await notifier.notify(StoreEvent(verb="create", item={"id": 2}))
        await notifier.notify(StoreEvent(verb="update", item={"id": 1}))

    # Should receive single batch event
    assert len(events) == 1
    assert events[0].verb == "batch"
    assert events[0].item["count"] == 3
    assert set(events[0].item["verbs"]) == {"create", "update"}


async def test_batch_no_events(notifier):
    """Empty batch context fires no events"""
    events = []
    notifier.add_observer(lambda e: events.append(e))

    async with notifier.batch():
        pass  # No events

    assert len(events) == 0


async def test_batch_single_event(notifier):
    """Single event in batch is delivered as-is (not wrapped)"""
    events = []
    notifier.add_observer(lambda e: events.append(e))

    async with notifier.batch():
        await notifier.notify(StoreEvent(verb="create", item={"id": 1}))

    assert len(events) == 1
    assert events[0].verb == "create"  # Not "batch"


async def test_nested_batch(notifier):
    """Nested batch contexts fire single event on outermost exit"""
    events = []
    notifier.add_observer(lambda e: events.append(e))

    async with notifier.batch():
        await notifier.notify(StoreEvent(verb="create", item={"id": 1}))
        async with notifier.batch():
            await notifier.notify(StoreEvent(verb="create", item={"id": 2}))
            async with notifier.batch():
                await notifier.notify(StoreEvent(verb="update", item={"id": 1}))
            # Inner batch exits - no event yet
            assert len(events) == 0
        # Middle batch exits - no event yet
        assert len(events) == 0
    # Outer batch exits - single event
    assert len(events) == 1
    assert events[0].item["count"] == 3


# --- Debouncing ---


async def test_debounce_coalesces_rapid_events(debounced_notifier):
    """Rapid events are coalesced after quiet period"""
    events = []
    debounced_notifier.add_observer(lambda e: events.append(e))

    # Fire events rapidly
    for i in range(5):
        await debounced_notifier.notify(StoreEvent(verb="create", item={"id": i}))

    # Events not delivered yet (debouncing)
    assert len(events) == 0

    # Wait for debounce to complete
    await asyncio.sleep(0.1)  # 100ms > 50ms debounce

    # Should receive single batch event
    assert len(events) == 1
    assert events[0].verb == "batch"
    assert events[0].item["count"] == 5


async def test_debounce_resets_on_new_event(debounced_notifier):
    """Debounce timer resets when new events arrive"""
    events = []
    debounced_notifier.add_observer(lambda e: events.append(e))

    # Fire first event
    await debounced_notifier.notify(StoreEvent(verb="create", item={"id": 1}))
    await asyncio.sleep(0.03)  # 30ms - not enough for 50ms debounce

    # Fire second event - should reset timer
    await debounced_notifier.notify(StoreEvent(verb="create", item={"id": 2}))
    await asyncio.sleep(0.03)  # Another 30ms

    # Still no events (timer reset)
    assert len(events) == 0

    # Wait for full debounce from last event
    await asyncio.sleep(0.05)  # 50ms more

    # Now should have batch event
    assert len(events) == 1
    assert events[0].item["count"] == 2


async def test_debounce_no_delay_when_disabled():
    """With debounce_ms=0, events are immediate"""
    notifier = EventNotifier(debounce_ms=0)
    events = []
    notifier.add_observer(lambda e: events.append(e))

    await notifier.notify(StoreEvent(verb="create", item={"id": 1}))
    await notifier.notify(StoreEvent(verb="create", item={"id": 2}))

    # Both events delivered immediately (separate)
    assert len(events) == 2


async def test_batch_bypasses_debounce(debounced_notifier):
    """Batch context flushes immediately, bypassing debounce"""
    events = []
    debounced_notifier.add_observer(lambda e: events.append(e))

    async with debounced_notifier.batch():
        await debounced_notifier.notify(StoreEvent(verb="create", item={"id": 1}))
        await debounced_notifier.notify(StoreEvent(verb="create", item={"id": 2}))

    # Events delivered immediately on batch exit (no debounce delay)
    assert len(events) == 1


async def test_debounce_after_batch(debounced_notifier):
    """Normal debouncing resumes after batch context"""
    events = []
    debounced_notifier.add_observer(lambda e: events.append(e))

    # First: batch (immediate)
    async with debounced_notifier.batch():
        await debounced_notifier.notify(StoreEvent(verb="create", item={"id": 1}))

    assert len(events) == 1

    # Second: normal event (debounced)
    await debounced_notifier.notify(StoreEvent(verb="create", item={"id": 2}))

    # Not delivered yet
    assert len(events) == 1

    # Wait for debounce
    await asyncio.sleep(0.1)

    assert len(events) == 2
