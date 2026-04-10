"""
ng_rdm - Reactive state management for NiceGUI with Tortoise ORM

Provides:
- Store layer: DictStore, TortoiseStore, MultitenantTortoiseStore
- Model helpers: QModel, FieldSpec, Validator
- Utilities: Date/time conversion, validation helpers
- Debug: Event stream visualization for debugging
"""

from .store import Store, StoreEvent, DictStore, StoreRegistry, store_registry
from .store import TortoiseStore, MultitenantTortoiseStore, MultitenantStoreRegistry, mt_store_registry, TenancyError, init_db
from .models import FieldSpec, Validator, QModel
from .debug import enable_debug_page
from .utils import logger, configure_logging

from importlib.metadata import PackageNotFoundError, version
try:
    __version__ = version("nicegui-rdm")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    # Store layer
    'Store',
    'StoreEvent',
    'DictStore',
    'StoreRegistry',
    'store_registry',
    'TortoiseStore',
    'MultitenantTortoiseStore',
    'MultitenantStoreRegistry',
    'mt_store_registry',
    'TenancyError',
    'init_db',

    # Model helpers
    'FieldSpec',
    'Validator',
    'QModel',

    # Debug
    'enable_debug_page',

    # Logging
    'logger',
    'configure_logging',
]
