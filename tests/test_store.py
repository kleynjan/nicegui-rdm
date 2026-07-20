"""
Tests for DictStore: CRUD operations, validation, observers, sorting, derived fields.
"""
import logging
import pytest
from ng_rdm.store import DictStore, StoreEvent, StoreRegistry
from ng_rdm.models import FieldSpec, Validator


# --- Basic CRUD ---

async def test_create_item(dict_store):
    """Create an item and verify it gets an id"""
    item = await dict_store.create_item({"name": "Alice"})
    assert item is not None
    assert "id" in item
    assert item["name"] == "Alice"


async def test_read_items(dict_store):
    """Read all items from store"""
    await dict_store.create_item({"name": "Alice"})
    await dict_store.create_item({"name": "Bob"})
    items = await dict_store.read_items()
    assert len(items) == 2


async def test_read_items_with_filter(dict_store):
    """Filter items by field value"""
    await dict_store.create_item({"name": "Alice", "role": "admin"})
    await dict_store.create_item({"name": "Bob", "role": "user"})
    await dict_store.create_item({"name": "Carol", "role": "admin"})

    admins = await dict_store.read_items(filter_by={"role": "admin"})
    assert len(admins) == 2
    assert all(a["role"] == "admin" for a in admins)


async def test_read_item_by_id(dict_store):
    """Read single item by ID"""
    created = await dict_store.create_item({"name": "Alice"})
    found = await dict_store.read_item_by_id(created["id"])
    assert found is not None
    assert found["name"] == "Alice"


async def test_read_item_by_id_not_found(dict_store):
    """Return None for non-existent ID"""
    result = await dict_store.read_item_by_id(999)
    assert result is None


async def test_update_item(dict_store):
    """Update an existing item"""
    created = await dict_store.create_item({"name": "Alice"})
    updated = await dict_store.update_item(created["id"], {"name": "Alice B."})
    assert updated is not None
    assert updated["name"] == "Alice B."

    # Verify in store
    found = await dict_store.read_item_by_id(created["id"])
    assert found["name"] == "Alice B."


async def test_update_nonexistent_item(dict_store):
    """Update returns None for non-existent item"""
    result = await dict_store.update_item(999, {"name": "Ghost"})
    assert result is None


async def test_delete_item(dict_store):
    """Delete an item from store"""
    created = await dict_store.create_item({"name": "Alice"})
    await dict_store.delete_item(created)

    items = await dict_store.read_items()
    assert len(items) == 0


async def test_delete_item_without_id(dict_store):
    """Delete with no id dict logs error but doesn't crash"""
    await dict_store.delete_item({"name": "no-id"})  # should not raise


async def test_read_returns_deep_copy(dict_store):
    """Read items should return copies, not references to internal data"""
    await dict_store.create_item({"name": "Alice"})
    items = await dict_store.read_items()
    items[0]["name"] = "MUTATED"

    fresh = await dict_store.read_items()
    assert fresh[0]["name"] == "Alice"


# --- Validation ---

async def test_validation_passes(validated_store):
    """Valid item passes validation"""
    item = await validated_store.create_item({"name": "Alice", "email": "alice@example.com"})
    assert item is not None


async def test_validation_rejects_invalid(validated_store):
    """Invalid item is rejected"""
    item = await validated_store.create_item({"name": "Alice", "email": "no-at-sign"})
    assert item is None


async def test_validation_rejects_empty_required(validated_store):
    """Empty required field is rejected"""
    item = await validated_store.create_item({"name": "", "email": "x@y.com"})
    assert item is None


async def test_validation_normalizes(validated_store):
    """Normalizer transforms values"""
    item = await validated_store.create_item({"name": "Alice", "email": "  ALICE@Example.COM  "})
    assert item["email"] == "alice@example.com"


async def test_validate_method_returns_error_info(validated_store):
    """validate() returns structured error info"""
    is_valid, error = validated_store.validate({"email": "bad"})
    assert is_valid is False
    assert error["col_name"] == "email"
    assert "error_msg" in error


async def test_validation_on_update(validated_store):
    """Validation also runs on update"""
    item = await validated_store.create_item({"name": "Alice", "email": "a@b.com"})
    result = await validated_store.update_item(item["id"], {"email": "invalid"})
    assert result is None


# --- Observers ---

async def test_observer_notified_on_create(dict_store):
    """Observer receives create event"""
    events = []
    dict_store.add_observer(lambda e: events.append(e))

    await dict_store.create_item({"name": "Alice"})
    assert len(events) == 1
    assert events[0].verb == "create"
    assert events[0].item["name"] == "Alice"


async def test_observer_notified_on_update(dict_store):
    """Observer receives update event"""
    created = await dict_store.create_item({"name": "Alice"})

    events = []
    dict_store.add_observer(lambda e: events.append(e))

    await dict_store.update_item(created["id"], {"name": "Alice B."})
    assert len(events) == 1
    assert events[0].verb == "update"


async def test_observer_notified_on_delete(dict_store):
    """Observer receives delete event"""
    created = await dict_store.create_item({"name": "Alice"})

    events = []
    dict_store.add_observer(lambda e: events.append(e))

    await dict_store.delete_item(created)
    assert len(events) == 1
    assert events[0].verb == "delete"


async def test_multiple_observers(dict_store):
    """Multiple observers all receive events"""
    events_a, events_b = [], []
    dict_store.add_observer(lambda e: events_a.append(e))
    dict_store.add_observer(lambda e: events_b.append(e))

    await dict_store.create_item({"name": "Alice"})
    assert len(events_a) == 1
    assert len(events_b) == 1


async def test_async_observer(dict_store):
    """Async observers are awaited correctly"""
    events = []

    async def async_observer(event):
        events.append(event)

    dict_store.add_observer(async_observer)
    await dict_store.create_item({"name": "Alice"})
    assert len(events) == 1


async def test_observer_count(dict_store):
    """observer_count property tracks registered observers"""
    assert dict_store.observer_count == 0
    dict_store.add_observer(lambda e: None)
    assert dict_store.observer_count == 1
    dict_store.add_observer(lambda e: None)
    assert dict_store.observer_count == 2


async def test_no_observer_on_failed_validation(validated_store):
    """Observers are NOT notified when validation fails"""
    events = []
    validated_store.add_observer(lambda e: events.append(e))

    await validated_store.create_item({"name": "", "email": "a@b.com"})
    assert len(events) == 0


# --- Sorting ---

async def test_sort_key(dict_store):
    """Items sorted by configured sort key"""
    dict_store.set_sort_key(lambda item: item["name"])
    await dict_store.create_item({"name": "Charlie"})
    await dict_store.create_item({"name": "Alice"})
    await dict_store.create_item({"name": "Bob"})

    items = await dict_store.read_items()
    assert [i["name"] for i in items] == ["Alice", "Bob", "Charlie"]


async def test_sort_key_reverse(dict_store):
    """Reverse sort order"""
    dict_store.set_sort_key(lambda item: item["name"], reverse=True)
    await dict_store.create_item({"name": "Alice"})
    await dict_store.create_item({"name": "Charlie"})
    await dict_store.create_item({"name": "Bob"})

    items = await dict_store.read_items()
    assert [i["name"] for i in items] == ["Charlie", "Bob", "Alice"]


# --- Derived fields ---

async def test_derived_fields(dict_store):
    """Derived fields are computed on read"""
    dict_store.set_derived_fields({
        "full_name": lambda item: f"{item.get('first', '')} {item.get('last', '')}".strip()
    })
    await dict_store.create_item({"first": "Alice", "last": "Smith"})

    items = await dict_store.read_items()
    assert items[0]["full_name"] == "Alice Smith"


async def test_derived_field_rejected_in_order_by(dict_store):
    """Derived fields are computed after the read, so ordering by one is an error"""
    dict_store.set_derived_fields({"full_name": lambda item: item.get("first", "")})
    await dict_store.create_item({"first": "Alice"})

    with pytest.raises(ValueError, match="full_name"):
        await dict_store.read_items(order_by=["full_name"])
    with pytest.raises(ValueError, match="full_name"):
        await dict_store.read_items(order_by=["-full_name"])


async def test_derived_field_rejected_in_filter_and_group(dict_store):
    """Same guard applies to filter_by and to read_counts' group_by"""
    dict_store.set_derived_fields({"full_name": lambda item: item.get("first", "")})
    await dict_store.create_item({"first": "Alice"})

    with pytest.raises(ValueError, match="full_name"):
        await dict_store.read_items(filter_by={"full_name": "Alice"})
    with pytest.raises(ValueError, match="full_name"):
        await dict_store.read_counts(group_by="full_name")

    # Real fields are unaffected
    assert await dict_store.read_counts(group_by="first") == {"Alice": 1}


# --- query_map: making a derived field queryable ---

async def test_query_map_makes_a_derived_field_orderable(dict_store):
    """order_by on a mapped derived name uses the first real field behind it"""
    dict_store.set_derived_fields(
        {"full_name": lambda item: f"{item['first']} {item['last']}"},
        query_map={"full_name": ["last", "first"]},
    )
    await dict_store.create_item({"first": "Alice", "last": "Young"})
    await dict_store.create_item({"first": "Bob", "last": "Adams"})

    ordered = await dict_store.read_items(order_by=["full_name"])
    assert [i["last"] for i in ordered] == ["Adams", "Young"]      # ordered by `last`


async def test_search_q_expands_a_mapped_derived_field(dict_store):
    """search_q ORs across every field behind the derived name"""
    dict_store.set_derived_fields(
        {"full_name": lambda item: f"{item['first']} {item['last']}"},
        query_map={"full_name": ["first", "last"]},
    )
    await dict_store.create_item({"first": "Alice", "last": "Young"})
    await dict_store.create_item({"first": "Bob", "last": "Adams"})

    q = dict_store.search_q("adam", ["full_name"])
    assert [i["first"] for i in await dict_store.read_items(q=q)] == ["Bob"]
    q = dict_store.search_q("ali", ["full_name"])
    assert [i["first"] for i in await dict_store.read_items(q=q)] == ["Alice"]


async def test_search_q_is_empty_without_text_or_fields(dict_store):
    assert dict_store.search_q("", ["name"]) is None
    assert dict_store.search_q("x", []) is None


async def test_base_store_search_q_raises_rather_than_filtering_nothing():
    """A store that forgets to implement search_q must fail loudly — a None would make
    the search box silently do nothing."""
    from ng_rdm.store.base import Store

    class BareStore(Store):
        pass

    with pytest.raises(NotImplementedError, match="BareStore"):
        BareStore().search_q("ali", ["name"])


async def test_and_q_composes_both_predicates(dict_store):
    """and_q ANDs two predicates; a None side is 'no constraint'"""
    await dict_store.create_item({"name": "Alice", "kind": "x"})
    await dict_store.create_item({"name": "Alicia", "kind": "y"})

    search = dict_store.search_q("ali", ["name"])
    kind_x = (lambda item: item["kind"] == "x")

    both = dict_store.and_q(kind_x, search)
    assert [i["name"] for i in await dict_store.read_items(q=both)] == ["Alice"]
    assert dict_store.and_q(None, search) is search
    assert dict_store.and_q(kind_x, None) is kind_x


# --- q predicate (in-memory form) ---

async def test_read_items_callable_q(dict_store):
    """DictStore accepts q as a plain predicate, ANDed with filter_by"""
    for name, kind in [("Alice", "x"), ("Alicia", "y"), ("Bob", "x")]:
        await dict_store.create_item({"name": name, "kind": kind})

    hits = await dict_store.read_items(q=lambda it: "ali" in it["name"].lower())
    assert [i["name"] for i in hits] == ["Alice", "Alicia"]

    both = await dict_store.read_items(filter_by={"kind": "x"}, q=lambda it: "ali" in it["name"].lower())
    assert [i["name"] for i in both] == ["Alice"]


async def test_read_counts_callable_q(dict_store):
    for name in ["Alice", "Alicia", "Bob"]:
        await dict_store.create_item({"name": name})

    assert await dict_store.read_counts(q=lambda it: "ali" in it["name"].lower()) == 2


async def test_non_callable_q_rejected(dict_store):
    """A Tortoise Q (or anything else non-callable) still raises on the in-memory path"""
    with pytest.raises(NotImplementedError):
        await dict_store.read_items(q={"name": "Alice"})


# --- Bounded reads: limit / offset / order_by ---

async def test_read_items_order_by(dict_store):
    """order_by sorts in Python for DictStore, ascending and descending"""
    for name in ["Charlie", "Alice", "Bob"]:
        await dict_store.create_item({"name": name})

    asc = await dict_store.read_items(order_by=["name"])
    assert [i["name"] for i in asc] == ["Alice", "Bob", "Charlie"]

    desc = await dict_store.read_items(order_by=["-name"])
    assert [i["name"] for i in desc] == ["Charlie", "Bob", "Alice"]


async def test_read_items_limit_offset(dict_store):
    """limit/offset return the correct ordered slice"""
    for name in ["a", "b", "c", "d"]:
        await dict_store.create_item({"name": name})

    page = await dict_store.read_items(order_by=["name"], limit=2, offset=1)
    assert [i["name"] for i in page] == ["b", "c"]


# --- read_counts ---

async def test_read_counts_total_filtered_grouped(dict_store):
    await dict_store.create_item({"name": "A", "kind": "x"})
    await dict_store.create_item({"name": "B", "kind": "x"})
    await dict_store.create_item({"name": "C", "kind": "y"})

    assert await dict_store.read_counts() == 3
    assert await dict_store.read_counts(filter_by={"kind": "x"}) == 2
    assert await dict_store.read_counts(group_by="kind") == {"x": 2, "y": 1}


# --- Unbounded read warning ---

async def test_unbounded_read_warns_past_threshold(dict_store, caplog):
    """A fully-unbounded read above the threshold logs a warning"""
    dict_store.unbounded_warn_threshold = 3
    for i in range(5):
        await dict_store.create_item({"name": f"n{i}"})

    with caplog.at_level(logging.WARNING, logger="ng_rdm"):
        await dict_store.read_items()
    assert any("unbounded read" in r.message.lower() for r in caplog.records)


async def test_bounded_read_does_not_warn(dict_store, caplog):
    """No warning when limit or filter_by bound the read"""
    dict_store.unbounded_warn_threshold = 3
    for i in range(5):
        await dict_store.create_item({"name": f"n{i}"})

    with caplog.at_level(logging.WARNING, logger="ng_rdm"):
        await dict_store.read_items(limit=2)
        await dict_store.read_items(filter_by={"name": "n1"})
    assert not any("unbounded read" in r.message.lower() for r in caplog.records)


# --- StoreRegistry ---

def test_registry_register_and_get(registry):
    """Register and retrieve a store by name"""
    store = DictStore()
    registry.register_store("items", store)

    assert registry.get_store("items") is store


def test_registry_missing_store(registry):
    """KeyError when store not found"""
    with pytest.raises(KeyError, match="No store"):
        registry.get_store("nonexistent")


def test_registry_multiple_stores(registry):
    """Multiple named stores are independent"""
    store_a = DictStore()
    store_b = DictStore()
    registry.register_store("items", store_a)
    registry.register_store("users", store_b)

    assert registry.get_store("items") is store_a
    assert registry.get_store("users") is store_b
    assert registry.get_store("items") is not store_b


def test_registry_get_all_stores(registry):
    """get_all_stores returns (name, store) tuples"""
    store_a = DictStore()
    store_b = DictStore()
    registry.register_store("items", store_a)
    registry.register_store("users", store_b)

    all_stores = registry.get_all_stores()
    assert len(all_stores) == 2
    names = {name for name, _ in all_stores}
    assert names == {"items", "users"}


# --- Observer Remove/Topics ---


async def test_remove_observer(validated_store):
    """Removed observer no longer receives events"""
    events = []
    def observer(e): return events.append(e)
    validated_store.add_observer(observer)

    await validated_store.create_item({"email": "test@example.com", "name": "Test"})
    assert len(events) == 1

    validated_store.remove_observer(observer)
    await validated_store.create_item({"email": "test2@example.com", "name": "Test2"})
    assert len(events) == 1  # No new event


async def test_observer_with_topics(validated_store):
    """Observer with topics only receives matching events"""
    events_role5 = []
    events_all = []

    validated_store.add_observer(lambda e: events_role5.append(e), topics={"role_id": 5})
    validated_store.add_observer(lambda e: events_all.append(e))  # Wildcard

    await validated_store.create_item({"email": "test@example.com", "name": "Test", "role_id": 5})
    await validated_store.create_item({"email": "test2@example.com", "name": "Test2", "role_id": 7})

    assert len(events_role5) == 1  # Only role_id=5
    assert len(events_all) == 2  # Both events


async def test_set_topic_fields(validated_store):
    """set_topic_fields configures notifier"""
    validated_store.set_topic_fields(["role_id", "guest_id"])
    # Just verify it doesn't crash - internal state not exposed
    assert True
