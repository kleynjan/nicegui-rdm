"""
CRUD table component factory and re-exports.
"""

from .base import Column, TableConfig, CLASSES_PREFIX
from .direct import DirectEditTable
from .explicit import ExplicitEditTable, confirm_dialog
from .protocol import CrudDataSource


def create_crud_table(state: dict, data_source: CrudDataSource, config: TableConfig):
    """
    Factory function to create appropriate table implementation based on mode.

    Args:
        state: Dictionary to store table state
        data_source: Data source implementing CrudDataSource protocol (e.g., Store, API client)
        config: TableConfig with mode setting

    Returns:
        DirectEditTable or ExplicitEditTable instance based on config.mode
    """
    if config.mode == "direct":
        return DirectEditTable(state, data_source, config)
    else:
        return ExplicitEditTable(state, data_source, config)


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
