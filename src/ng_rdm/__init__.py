"""
ng_rdm - Reactive state management for NiceGUI with Tortoise ORM

Provides:
- Store layer: DictStore, TortoiseStore, MultitenantTortoiseStore
- Model helpers: RdmModel, MultitenantRdmModel, FieldSpec, Validator
- Utilities: Date/time conversion, validation helpers
- Debug: Event stream visualization for debugging
"""

from importlib.metadata import PackageNotFoundError, version

from .debug import enable_debug_page
from .models import FieldSpec, MultitenantRdmModel, RdmModel, Validator
from .store import (
    DictStore,
    MultitenantStoreRegistry,
    MultitenantTortoiseStore,
    Store,
    StoreEvent,
    StoreRegistry,
    TenancyError,
    TortoiseStore,
    init_db,
    mt_store_registry,
    set_valid_tenants,
    store_registry,
)
from .utils import configure_logging, logger

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
    'set_valid_tenants',
    'init_db',

    # Model helpers
    'FieldSpec',
    'Validator',
    'RdmModel',
    'MultitenantRdmModel',

    # Debug
    'enable_debug_page',

    # Logging
    'logger',
    'configure_logging',
]
