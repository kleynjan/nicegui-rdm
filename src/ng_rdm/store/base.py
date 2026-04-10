"""
Base store implementation providing core CRUD operations and validation.

A Store...
- maps a collection of items to underlying storage, eg dict or database table(s)
- it notifies registered observers of changes to the store, eg create, update, delete
  (to do this, it is an app-wide singleton per type, and optionally, tenant)
- it enables tenant separation by having one instance (per type) per tenant
- it performs validation and normalization of modified/new items before accepting them
- it is *not* meant for caching
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from ..models import FieldSpec
from ..utils import logger
from .notifier import EventNotifier, StoreEvent

if TYPE_CHECKING:
    from ..debug.event_log import EventLog


class Store:
    """Base store providing core CRUD operations and validation.
    (includes Q and join_fields interface for ORM subclasses)"""

    def __init__(self, field_specs: dict[str, FieldSpec] | None = None, debounce_ms: int = 0) -> None:
        self._notifier = EventNotifier(debounce_ms)
        self._field_specs: dict[str, FieldSpec] = field_specs or {}
        self._sort_key: Callable[[dict], Any] | None = None
        self._sort_reverse: bool = False
        self._derived_fields: dict[str, Callable[[dict], Any]] = {}
        self._derived_field_dependencies: list[str] = []

    def set_sort_key(self, key_func: Callable[[dict], Any], reverse: bool = False) -> None:
        """Set function to generate sort key from item"""
        self._sort_key = key_func
        self._sort_reverse = reverse

    def set_derived_fields(self, derived_fields: dict[str, Callable[[dict], Any]], dependencies: list[str] | None = None) -> None:
        """Set derived fields - computed values added to each item on read.

        Args:
            derived_fields: dict mapping field name to a function(item) → value
                Example: {'calc_guest_name': lambda row: ... or row.get('guest__user_id') or ''}
            dependencies: list of join fields required by derived field computations
                Example: ['guest__given_name', 'guest__family_name', 'guest__user_id']
        """
        self._derived_fields = derived_fields
        self._derived_field_dependencies = dependencies or []

    def _apply_derived_fields(self, items: list[dict]) -> list[dict]:
        """Apply derived field computations to items"""
        if not self._derived_fields:
            return items
        for item in items:
            for name, compute in self._derived_fields.items():
                item[name] = compute(item)
        return items

    def _sort_results(self, items: list[dict]) -> list[dict]:
        """Sort results if sort key is configured"""
        if self._sort_key and items:
            return sorted(items, key=self._sort_key, reverse=self._sort_reverse)
        return items

    @property
    def field_specs(self) -> dict[str, FieldSpec]:
        """Get field specs"""
        return self._field_specs

    @property
    def observer_count(self) -> int:
        """Get the number of observers"""
        return self._notifier.observer_count

    def set_event_log(self, event_log: EventLog, name: str, tenant: str = "") -> None:
        """Set the event log for debug tracking.

        Args:
            event_log: The EventLog instance to log events to
            name: Store name (for display in debug panel)
            tenant: Tenant identifier (for display in debug panel)
        """
        self._notifier.set_event_log(event_log, name, tenant)

    def validate(self, item: dict) -> tuple[bool, dict]:
        """Validate and normalize an item or partial.
        The item dict is modified in place for normalization.
        Returns (True, {}) if valid, or (False, error_info) if invalid."""
        for field, config in self._field_specs.items():
            if field in item:
                value = item[field]

                # Run all validators
                for validator in config.validators:
                    if not validator.validator(value, item):
                        return (
                            False,
                            {
                                "col_name": field,
                                "error_msg": validator.message,
                                "error_value": value,
                            },
                        )

                # Normalize if normalizer exists
                if config.normalizer and value is not None:
                    item[field] = config.normalizer(value)

        return (True, {})

    async def notify_observers(self, event: StoreEvent) -> None:
        """Notify observers of store events"""
        await self._notifier.notify(event)

    def set_topic_fields(self, fields: list[str]) -> None:
        """Configure which item fields can be used for topic-based routing."""
        self._notifier.set_topic_fields(fields)

    def add_observer(self, observer: Callable[[StoreEvent], Any], topics: dict[str, Any] | None = None) -> None:
        """Add observer with optional topic subscription."""
        self._notifier.add_observer(observer, topics)

    def remove_observer(self, observer: Callable[[StoreEvent], Any]) -> None:
        """Remove observer by callback identity."""
        self._notifier.remove_observer(observer)

    def batch(self):
        """Context manager for explicit batching of notifications.

        Usage:
            async with store.batch():
                await store.create_item(item1)
                await store.create_item(item2)
            # Single batch event fires here
        """
        return self._notifier.batch()

    # CRUD interface that subclasses must implement
    async def _create_item(self, item: dict) -> dict:
        raise NotImplementedError()

    async def _read_items(self, filter_by: dict | None = None, q: Any | None = None, join_fields: list[str] = []) -> list[dict]:
        raise NotImplementedError()

    async def _update_item(self, id: int, partial_item: dict) -> dict | None:
        raise NotImplementedError()

    async def _delete_item(self, id: int) -> None:
        raise NotImplementedError()

    # Public CRUD API with validation and events
    async def create_item(self, item: dict) -> dict | None:
        """Create an item with validation"""
        is_valid, error = self.validate(item)
        if not is_valid:
            logger.error(f"Validation error creating item: {error}")
            return None
        created_item = await self._create_item(item)
        await self.notify_observers(StoreEvent(verb="create", item=created_item))
        return created_item

    async def read_items(self, filter_by: dict | None = None, q: Any | None = None, join_fields: list[str] = []) -> list[dict]:
        """Read items with optional filtering; applies derived fields and sorts.

        Args:
            filter_by: dict of field=value pairs for equality filtering (AND)
            q: Q object for complex queries (for advanced use cases) (to implement in ORM subclass)
            join_fields: list of fields to join (to implement in ORM subclass)
        """
        # Merge requested join_fields with derived field dependencies
        all_join_fields = list(set(join_fields + self._derived_field_dependencies))

        items = await self._read_items(filter_by, q, all_join_fields)
        items = self._apply_derived_fields(items)
        return self._sort_results(items)

    async def read_item_by_id(self, id: int, join_fields: list[str] = []) -> dict | None:
        """Read a single item by ID, with optional join fields."""
        items = await self._read_items(filter_by={"id": id}, join_fields=join_fields)
        if not items:
            return None
        return items[0]

    async def update_item(self, id: int, partial_item: dict) -> dict | None:
        """Update an item with validation"""
        is_valid, error = self.validate(partial_item)
        if not is_valid:
            logger.error(f"Validation error updating item: {error}")
            return None
        updated_item = await self._update_item(id, partial_item)
        if updated_item:
            await self.notify_observers(StoreEvent(verb="update", item=updated_item))
        return updated_item

    async def delete_item(self, item: dict) -> None:
        """Delete an item"""
        if isinstance(item, dict) and "id" in item:
            await self._delete_item(item["id"])
            await self.notify_observers(StoreEvent(verb="delete", item=item))
        else:
            logger.error(f"Cannot delete item without id: {item}")


class StoreRegistry:
    """Registry for singleton store instances keyed by name."""

    def __init__(self):
        self._stores: dict[str, Store] = {}
        self._event_log: EventLog | None = None

    def set_event_log(self, event_log: EventLog) -> None:
        """Enable debug event logging for all stores.

        Wires up event logging for all currently registered stores
        and any stores registered in the future.
        """
        self._event_log = event_log
        for name, store in self._stores.items():
            store.set_event_log(event_log, name)

    def register_store(self, name: str, store: Store) -> None:
        """Register a store instance by name."""
        self._stores[name] = store
        if self._event_log:
            store.set_event_log(self._event_log, name)
        logger.debug(f"Registered {name} store")

    def get_store(self, name: str) -> Store:
        """Get the singleton store instance by name.

        Raises:
            KeyError: If no store exists for this name
        """
        try:
            return self._stores[name]
        except KeyError:
            raise KeyError(f"No store '{name}' registered")

    def get_all_stores(self) -> list[tuple[str, Store]]:
        """Get all registered stores as (name, store) tuples."""
        return list(self._stores.items())


# Global registry instance
store_registry = StoreRegistry()
