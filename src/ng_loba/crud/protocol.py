"""
Protocol defining the interface needed by CRUD tables.

This allows CRUD tables to work with any data source that implements
the required methods, not just Store instances.
"""

from typing import Protocol, Any, Callable

# Import StoreEvent from store.base - it's simple and generic enough to reuse
from ..store.base import StoreEvent


class CrudDataSource(Protocol):
    """Protocol defining the interface needed by CRUD tables.

    Any class implementing these methods can be used as a data source
    for CRUD tables, including Store, REST API clients, mock data sources, etc.

    The protocol uses structural subtyping - classes don't need to explicitly
    inherit from this protocol, they just need to implement the methods.
    """

    # CRUD Operations (Required)
    async def create_item(self, item: dict) -> dict | None:
        """Create a new item. Returns created item with id, or None on failure."""
        ...

    async def read_items(
        self,
        filter_by: dict | None = None,
        q: Any | None = None,
        join_fields: list[str] = []
    ) -> list[dict]:
        """Read items with optional filtering and joins."""
        ...

    async def update_item(self, id: int, partial_item: dict) -> dict | None:
        """Update an item. Returns updated item or None on failure."""
        ...

    async def delete_item(self, item: dict) -> None:
        """Delete an item."""
        ...

    def validate(self, item: dict) -> tuple[bool, dict]:
        """Validate an item or partial.

        Returns:
            (True, {}) if valid
            (False, {'col_name': str, 'error_msg': str, 'error_value': Any}) if invalid
        """
        ...

    # Observer Pattern (Optional - for external changes)
    # Note: This is optional. Data sources that don't support real-time updates
    # can omit this method or provide a no-op implementation.
    def add_observer(self, observer: Callable[[StoreEvent], Any]) -> None:
        """Add an observer to receive store events.

        This method is optional. Data sources that don't support 
        real-time updates can provide a no-op implementation or omit it.

        Args:
            observer: Async or sync function that receives StoreEvent notifications
        """
        ...
