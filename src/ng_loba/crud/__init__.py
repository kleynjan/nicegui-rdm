"""
CRUD components for data management.
"""

from .table import CrudTable, Column, TableConfig, init_page
from .keyboard import ObservableKeyboard

__all__ = ['CrudTable', 'Column', 'TableConfig', 'ObservableKeyboard', 'init_page']
