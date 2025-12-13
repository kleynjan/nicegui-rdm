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

import copy
import inspect
from dataclasses import dataclass
from typing import Any, Callable

from ..models import FieldSpec
from ..utils import logger


@dataclass
class StoreEvent:
    """Store events / notifications, sent to store observers"""
    verb: str
    item: dict


class Store:
    """Base store providing core CRUD operations and validation.
    (includes Q and join_fields interface for ORM subclasses)"""

    def __init__(self, field_specs: dict[str, FieldSpec] | None = None) -> None:
        self._observers: list[Callable[[StoreEvent], Any]] = []
        self._field_specs: dict[str, FieldSpec] = field_specs or {}
        self._sort_key: Callable[[dict], Any] | None = None
        self._sort_reverse: bool = False

    def set_sort_key(self, key_func: Callable[[dict], Any], reverse: bool = False) -> None:
        """Set function to generate sort key from item"""
        self._sort_key = key_func
        self._sort_reverse = reverse

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
        return len(self._observers)

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
        # logger.debug(f"Notifying {len(self._observers)} observers: {self.__class__.__name__} {event}")
        for observer in self._observers:
            if inspect.iscoroutinefunction(observer):
                await observer(event)
            else:
                observer(event)

    def add_observer(self, observer: Callable[[StoreEvent], Any]) -> None:
        """Add an observer to receive store events"""
        self._observers.append(observer)

    # CRUD interface that subclasses must implement
    async def _create_item(self, item: dict) -> dict:
        raise NotImplementedError()

    async def _read_items(self, filter_by: dict | None = None, q: Any | None = None, join_fields: list[str] = []) -> list[dict]:
        raise NotImplementedError()

    async def _update_item(self, id: int, partial_item: dict) -> dict | None:
        raise NotImplementedError()

    async def _delete_item(self, id: int) -> None:
        raise NotImplementedError()

    async def read_item_by_id(self, id: int, join_fields: list[str] = []) -> dict | None:
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
        """Read items with optional filtering; sorts items if _sort_key is defined.

        Args:
            filter_by: dict of field=value pairs for equality filtering (AND)
            q: Q object for complex queries (for advanced use cases) (to implement in ORM subclass)
            join_fields: list of fields to join (to implement in ORM subclass)
        """
        items = await self._read_items(filter_by, q, join_fields)
        return self._sort_results(items)

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


# Example store implementation

class DictStore(Store):
    """In-memory dictionary-based store implementation"""
    def __init__(self, field_specs: dict[str, FieldSpec] | None = None) -> None:
        super().__init__(field_specs)
        self._items = []

    def _id_to_row_index(self, id: int) -> int | None:
        """Convert item ID to row index"""
        for i, item in enumerate(self._items):
            if item["id"] == id:
                return i
        return None

    async def _create_item(self, item: dict) -> dict:
        if "id" not in item:
            item["id"] = len(self._items)
        self._items.append(item)
        return item

    async def _read_items(self, filter_by: dict | None = None, q: Any | None = None, join_fields: list[str] = []) -> list[dict]:
        if q or join_fields:
            raise NotImplementedError("ORM arguments q and join_fields not supported")

        items = copy.deepcopy(self._items)
        if filter_by:
            filtered_items = []
            for item in items:
                matches = True
                for key, value in filter_by.items():
                    if key not in item or item[key] != value:
                        matches = False
                        break
                if matches:
                    filtered_items.append(item)
            items = filtered_items
        return items

    async def _update_item(self, id: int, new_partial_item: dict) -> dict | None:
        new_partial_item.pop("id", None)
        for item in self._items:
            if item["id"] == id:
                item.update(new_partial_item)
                return item
        return None

    async def _delete_item(self, id: int) -> None:
        for i, it in enumerate(self._items):
            if it["id"] == id:
                self._items.pop(i)
                return

    async def read_item_by_id(self, id: int) -> dict | None:
        for item in self._items:
            if item["id"] == id:
                return item
        return None
