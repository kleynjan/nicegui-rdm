"""
ng_rdm - Reactive state management for NiceGUI with Tortoise ORM

Provides:
- Store layer: DictStore, TortoiseStore, MultitenantTortoiseStore
- Model helpers: QModel, FieldSpec, Validator
- Utilities: Date/time conversion, validation helpers
"""

from .store import Store, StoreEvent, DictStore, StoreRegistry, store_registry
from .store import TortoiseStore, MultitenantTortoiseStore, TenancyError, init_db
from .models import FieldSpec, Validator, QModel

__version__ = "0.1.0"

__all__ = [
    # Store layer
    'Store',
    'StoreEvent',
    'DictStore',
    'StoreRegistry',
    'store_registry',
    'TortoiseStore',
    'MultitenantTortoiseStore',
    'TenancyError',
    'init_db',

    # Model helpers
    'FieldSpec',
    'Validator',
    'QModel',
]
