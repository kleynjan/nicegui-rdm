"""
Tests for DictStore: CRUD operations, validation, observers, sorting, derived fields.
"""
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


# --- StoreRegistry ---

def test_registry_register_and_get(registry):
    """Register and retrieve a store"""
    store = DictStore()
    registry.register_store("tenant_a", "items", store)

    retrieved = registry.get_store("tenant_a", "items")
    assert retrieved is store


def test_registry_missing_rdm(registry):
    """KeyError when store not found"""
    with pytest.raises(KeyError, match="No store"):
        registry.get_store("tenant_a", "nonexistent")


def test_registry_tenant_isolation(registry):
    """Stores are isolated per tenant"""
    store_a = DictStore()
    store_b = DictStore()
    registry.register_store("tenant_a", "items", store_a)
    registry.register_store("tenant_b", "items", store_b)

    assert registry.get_store("tenant_a", "items") is store_a
    assert registry.get_store("tenant_b", "items") is store_b
    assert registry.get_store("tenant_a", "items") is not store_b
