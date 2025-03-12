"""
ng_loba - Line of Business Application components for NiceGUI
"""

from .store.base import Store, StoreEvent, DictStore
from .store.orm import TortoiseStore, init_db
from .refreshable.core import StatefulRefreshable, StoreRefreshable
from .crud.table import CrudTable, Column, TableConfig, init_page
from .utils.types import Validator, FieldSpec
from .utils.logging import setup_logging

__version__ = "0.1.0"

__all__ = [
    # Store
    'Store',
    'StoreEvent',
    'DictStore',
    'TortoiseStore',
    'init_db',

    # Refreshable
    'StatefulRefreshable',
    'StoreRefreshable',

    # CRUD
    'CrudTable',
    'Column',
    'TableConfig',

    # Utils
    'Validator',
    'FieldSpec',
    'setup_logging',
    'init_page',
]
