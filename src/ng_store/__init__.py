"""
ng_store - Reactive state management for NiceGUI with Tortoise ORM

Provides:
- Store layer: DictStore, TortoiseStore, MultitenantTortoiseStore
- Refreshable components: StatefulRefreshable, StoreRefreshable
- Model helpers: QModel, FieldSpec, Validator
- Utilities: Date/time conversion, validation helpers
"""

from .store import Store, StoreEvent, DictStore, StoreRegistry, store_registry
from .store import TortoiseStore, MultitenantTortoiseStore, TenancyError, init_db
from .refreshable import StatefulRefreshable, StoreRefreshable
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

    # Refreshable components
    'StatefulRefreshable',
    'StoreRefreshable',

    # Model helpers
    'FieldSpec',
    'Validator',
    'QModel',
]
