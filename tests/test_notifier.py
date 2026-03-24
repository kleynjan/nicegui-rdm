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


# --- Remove Observer ---


async def test_remove_observer(notifier):
    """Removed observer no longer receives events"""
    events = []
    def observer(e): return events.append(e)
    notifier.add_observer(observer)

    await notifier.notify(StoreEvent(verb="create", item={"id": 1}))
    assert len(events) == 1

    notifier.remove_observer(observer)
    await notifier.notify(StoreEvent(verb="create", item={"id": 2}))
    assert len(events) == 1  # No new event received


async def test_remove_observer_count(notifier):
    """remove_observer decreases observer count"""
    def observer1(e): return None
    def observer2(e): return None
    notifier.add_observer(observer1)
    notifier.add_observer(observer2)
    assert notifier.observer_count == 2

    notifier.remove_observer(observer1)
    assert notifier.observer_count == 1


# --- Topic Filtering ---


async def test_topic_filtering_exact_match(notifier):
    """Observer with topics only receives matching events"""
    events_role5 = []
    events_role7 = []

    notifier.add_observer(lambda e: events_role5.append(e), topics={"role_id": 5})
    notifier.add_observer(lambda e: events_role7.append(e), topics={"role_id": 7})

    await notifier.notify(StoreEvent(verb="update", item={"id": 1, "role_id": 5}))

    assert len(events_role5) == 1
    assert len(events_role7) == 0


async def test_topic_wildcard_receives_all(notifier):
    """Observer with topics=None receives all events"""
    all_events = []
    role5_events = []

    notifier.add_observer(lambda e: all_events.append(e))  # Wildcard
    notifier.add_observer(lambda e: role5_events.append(e), topics={"role_id": 5})

    await notifier.notify(StoreEvent(verb="create", item={"id": 1, "role_id": 5}))
    await notifier.notify(StoreEvent(verb="create", item={"id": 2, "role_id": 7}))

    assert len(all_events) == 2  # Wildcard gets both
    assert len(role5_events) == 1  # Filtered gets only matching


async def test_topic_compound_match(notifier):
    """Compound topics require all fields to match"""
    events = []
    notifier.add_observer(
        lambda e: events.append(e),
        topics={"role_id": 5, "guest_id": 100}
    )

    # Both fields match
    await notifier.notify(StoreEvent(verb="update", item={"role_id": 5, "guest_id": 100}))
    assert len(events) == 1

    # Only one field matches
    await notifier.notify(StoreEvent(verb="update", item={"role_id": 5, "guest_id": 200}))
    assert len(events) == 1  # No new event


async def test_batch_notifies_all_observers(notifier):
    """Batch events notify all observers regardless of topics (conservative)"""
    events_role5 = []
    events_role7 = []

    notifier.add_observer(lambda e: events_role5.append(e), topics={"role_id": 5})
    notifier.add_observer(lambda e: events_role7.append(e), topics={"role_id": 7})

    async with notifier.batch():
        await notifier.notify(StoreEvent(verb="update", item={"id": 1, "role_id": 5}))
        await notifier.notify(StoreEvent(verb="update", item={"id": 2, "role_id": 7}))

    # Both observers receive batch event (conservative approach)
    assert len(events_role5) == 1
    assert len(events_role7) == 1
    assert events_role5[0].verb == "batch"
