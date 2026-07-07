"""
Tests for EventNotifier: notification, throttling, batching.
"""
import asyncio
import pytest
from ng_rdm.store import EventNotifier, StoreEvent


@pytest.fixture
def notifier():
    """A fresh EventNotifier with no throttling"""
    return EventNotifier(throttle_ms=0)


@pytest.fixture
def throttled_notifier():
    """EventNotifier with a 50ms throttle interval"""
    return EventNotifier(throttle_ms=50)


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


# --- Throttling (leading + trailing) ---


async def test_throttle_leading_flush_is_immediate(throttled_notifier):
    """After a quiet period, the first event flushes immediately (leading edge)."""
    events = []
    throttled_notifier.add_observer(lambda e: events.append(e))

    await throttled_notifier.notify(StoreEvent(verb="create", item={"id": 1}))

    # No wait needed - leading edge fires right away (unlike a trailing debounce)
    assert len(events) == 1
    assert events[0].verb == "create"


async def test_throttle_coalesces_after_leading(throttled_notifier):
    """Leading event fires immediately; the rest coalesce into one trailing flush."""
    events = []
    throttled_notifier.add_observer(lambda e: events.append(e))

    for i in range(5):
        await throttled_notifier.notify(StoreEvent(verb="create", item={"id": i}))

    # Leading event delivered; events 2..5 are still pending
    assert len(events) == 1
    assert events[0].verb == "create"

    # Trailing flush at the interval boundary coalesces the remaining 4
    await asyncio.sleep(0.1)
    assert len(events) == 2
    assert events[1].verb == "batch"
    assert events[1].item["count"] == 4


async def test_throttle_trailing_flush_after_last_event(throttled_notifier):
    """A guaranteed trailing flush delivers the final coalesced events."""
    events = []
    throttled_notifier.add_observer(lambda e: events.append(e))

    await throttled_notifier.notify(StoreEvent(verb="create", item={"id": 1}))  # leading
    await throttled_notifier.notify(StoreEvent(verb="create", item={"id": 2}))  # coalesced
    assert len(events) == 1

    await asyncio.sleep(0.08)
    assert len(events) == 2  # trailing flush delivered event 2


async def test_throttle_does_not_starve_under_sustained_load(throttled_notifier):
    """A sustained sub-interval stream flushes on a steady cadence (never starves)."""
    flushes = []
    throttled_notifier.add_observer(lambda e: flushes.append(e))

    # Fire every ~10ms for ~130ms; throttle interval is 50ms.
    total = 13
    for i in range(total):
        await throttled_notifier.notify(StoreEvent(verb="create", item={"id": i}))
        await asyncio.sleep(0.01)

    # A pure trailing debounce would still be at 0 here; throttle has flushed
    # the leading edge plus at least one mid-stream boundary.
    assert len(flushes) >= 2

    # After quiescence the trailing flush settles; every event was delivered exactly once.
    await asyncio.sleep(0.08)
    delivered = sum(f.item.get("count", 1) for f in flushes)
    assert delivered == total
    # Steady cadence: at most ~one flush per interval over the window (+ leading/trailing slack)
    assert len(flushes) <= 6


async def test_throttle_no_delay_when_disabled():
    """With throttle_ms=0, events are immediate and separate"""
    notifier = EventNotifier(throttle_ms=0)
    events = []
    notifier.add_observer(lambda e: events.append(e))

    await notifier.notify(StoreEvent(verb="create", item={"id": 1}))
    await notifier.notify(StoreEvent(verb="create", item={"id": 2}))

    assert len(events) == 2


async def test_batch_bypasses_throttle(throttled_notifier):
    """Batch context flushes immediately, bypassing the throttle interval"""
    events = []
    throttled_notifier.add_observer(lambda e: events.append(e))

    async with throttled_notifier.batch():
        await throttled_notifier.notify(StoreEvent(verb="create", item={"id": 1}))
        await throttled_notifier.notify(StoreEvent(verb="create", item={"id": 2}))

    # Events delivered immediately on batch exit (no throttle delay)
    assert len(events) == 1


async def test_throttle_after_batch(throttled_notifier):
    """Throttling resumes after a batch context; the next event flushes on the boundary"""
    events = []
    throttled_notifier.add_observer(lambda e: events.append(e))

    # First: batch flushes immediately and stamps the throttle boundary
    async with throttled_notifier.batch():
        await throttled_notifier.notify(StoreEvent(verb="create", item={"id": 1}))
    assert len(events) == 1

    # Second: within the interval of the batch flush → coalesced, not immediate
    await throttled_notifier.notify(StoreEvent(verb="create", item={"id": 2}))
    assert len(events) == 1

    # Trailing flush delivers it
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
