"""
In-memory dictionary-based store implementation.

DictStore is useful for testing and prototyping without database setup.
"""

import copy
from typing import Any

from ..models import FieldSpec
from .base import Store


class DictStore(Store):
    """In-memory dictionary-based store implementation"""

    def __init__(self, field_specs: dict[str, FieldSpec] | None = None) -> None:
        super().__init__(field_specs)
        self._items: list[dict] = []

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
