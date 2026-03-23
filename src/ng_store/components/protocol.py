"""
Protocol defining the interface needed by CRUD components.

This allows CRUD components to work with any data source that implements
the required methods, not just Store instances.
"""

from typing import Protocol, Any, Callable


class CrudDataSource(Protocol):
    """Protocol defining the interface needed by CRUD components.

    Any class implementing these methods can be used as a data source
    for CRUD components, including Store, REST API clients, mock data sources, etc.

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

    # Observer Pattern (Required - for automatic UI refresh)
    # Note: This is now required for CRUD tables to work correctly.
    # CRUD tables rely on data source notifications to refresh automatically
    # after create/update/delete operations.
    def add_observer(self, observer: Callable[[Any], Any]) -> None:
        """Add an observer to receive CRUD events.

        This method is required for CRUD components to function correctly.
        CRUD components register as observers and automatically refresh when
        data changes occur (create/update/delete operations).

        Args:
            observer: Async or sync function that receives event notifications.
                     Called after each successful CRUD operation.
                     Event is StoreEvent (from ng_store.store).
        """
        ...
