"""
CRUD table component factory and re-exports.
"""

from .base import Column, TableConfig, CLASSES_PREFIX
from .direct import DirectEditTable
from .explicit import ExplicitEditTable, confirm_dialog
from ..store.base import Store


def create_crud_table(state: dict, store: Store, config: TableConfig):
    """
    Factory function to create appropriate table implementation based on mode.

    Args:
        state: Dictionary to store table state
        store: Store instance for data operations
        config: TableConfig with mode setting

    Returns:
        DirectEditTable or ExplicitEditTable instance based on config.mode
    """
    if config.mode == "direct":
        return DirectEditTable(state, store, config)
    else:
        return ExplicitEditTable(state, store, config)


# Backwards compatibility - CrudTable is now an alias for ExplicitEditTable
CrudTable = ExplicitEditTable

# Re-export commonly used items
__all__ = [
    'create_crud_table',
    'CrudTable',
    'DirectEditTable',
    'ExplicitEditTable',
    'Column',
    'TableConfig',
    'confirm_dialog',
    'CLASSES_PREFIX',
]
