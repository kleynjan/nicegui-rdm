# ng-store

Reactive state management for NiceGUI applications with Tortoise ORM.

## Overview

ng-store provides a coarse-grained, persistent state management layer for NiceGUI applications:

- **Store Layer** — Observer pattern for database-backed state with automatic UI refresh
- **Refreshable Components** — `@ui.refreshable` wrappers that auto-update on store changes
- **Model Helpers** — Validation, field specs, and extended Tortoise ORM base class
- **Multi-tenancy** — Built-in tenant scoping for SaaS applications

## Installation

```bash
pip install ng-store
```

## Quick Start

```python
from nicegui import ui
from ng_store import DictStore, StoreRefreshable, FieldSpec, Validator

# Define validation
name_validator = Validator(
    message="Name cannot be empty",
    validator=lambda v, _: bool(v.strip())
)

# Create a store
store = DictStore({'name': FieldSpec(validators=[name_validator])})

# Create a refreshable component that auto-updates on store changes
class PersonList(StoreRefreshable):
    def __init__(self, store):
        super().__init__(store)
    
    async def _rebuild(self):
        items = await self.data_source.read_items()
        for item in items:
            ui.label(f"{item['name']}")

@ui.page('/')
async def main():
    person_list = PersonList(store)
    await person_list.build()
    
    # This will auto-refresh the list
    ui.button('Add', on_click=lambda: store.create_item({'name': 'New Person'}))

ui.run()
```

## Architecture

```
┌──────────────────────────────────────────────────────┐
│ NiceGUI UI Layer (@ui.refreshable components)        │
└────────────────────┬─────────────────────────────────┘
                     │ automatic refresh
                     ↓
┌──────────────────────────────────────────────────────┐
│ Refreshable Components                               │
│ - StatefulRefreshable (state dict + refresh)         │
│ - StoreRefreshable (+ store observer integration)    │
└────────────────────┬─────────────────────────────────┘
                     │ observer notification
                     ↓
┌──────────────────────────────────────────────────────┐
│ Store Layer (State Management & Data Access)         │
│ - Store (base abstract class)                        │
│ - DictStore (in-memory)                              │
│ - TortoiseStore (ORM-backed)                         │
│ - MultitenantTortoiseStore (tenant-scoped)           │
│ - StoreRegistry (singleton management)               │
└────────────────────┬─────────────────────────────────┘
                     │ database I/O
                     ↓
┌──────────────────────────────────────────────────────┐
│ Data Layer                                           │
│ - Tortoise ORM                                       │
│ - QModel (extended ORM base with validation)         │
└──────────────────────────────────────────────────────┘
```

## Store Types

### DictStore

In-memory store for prototyping and testing:

```python
from ng_store import DictStore, FieldSpec, Validator

store = DictStore({
    'email': FieldSpec(validators=[
        Validator("Invalid email", lambda v, _: '@' in v if v else True)
    ])
})

await store.create_item({'name': 'Alice', 'email': 'alice@example.com'})
items = await store.read_items()
await store.update_item(1, {'name': 'Alice Smith'})
await store.delete_item({'id': 1})
```

### TortoiseStore

Database-backed store with Tortoise ORM:

```python
from ng_store import TortoiseStore, init_db
from tortoise import fields
from tortoise.models import Model

class Person(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    email = fields.CharField(max_length=100, null=True)

# Initialize database
await init_db('sqlite://:memory:', modules={'models': ['__main__']})

# Create store
store = TortoiseStore(model=Person)
```

### MultitenantTortoiseStore

Automatic tenant scoping for SaaS:

```python
from ng_store import MultitenantTortoiseStore

store = MultitenantTortoiseStore(
    model=Person,
    tenant_field='org_id'
)

# Set valid tenants for the current user
store.set_valid_tenants([1, 2, 3])
store.set_tenant(1)

# All queries now automatically filter by org_id=1
items = await store.read_items()
```

## Observer Pattern

Stores notify observers on any change:

```python
from ng_store import StoreEvent

async def on_change(event: StoreEvent):
    print(f"{event.verb}: {event.item}")

store.add_observer(on_change)
```

## Validation

Define field validators and normalizers:

```python
from ng_store import FieldSpec, Validator

field_specs = {
    'email': FieldSpec(
        validators=[
            Validator("Required", lambda v, _: bool(v)),
            Validator("Invalid email", lambda v, _: '@' in v),
        ],
        normalizer=lambda v: v.lower().strip()
    ),
    'age': FieldSpec(
        validators=[
            Validator("Must be positive", lambda v, _: v > 0 if v else True),
        ]
    )
}

store = DictStore(field_specs)
valid, error = store.validate({'email': 'test', 'age': -1})
# valid=False, error={'col_name': 'email', 'error_msg': 'Invalid email', ...}
```

## Integration with ng-crud

For ready-made CRUD UI components, install [ng-crud](https://pypi.org/project/ng-crud/):

```bash
pip install ng-crud
```

ng-crud provides DataTable, EditDialog, ViewStack, and other components that work seamlessly with ng-store.

## Requirements

- Python 3.12+
- NiceGUI >= 1.4.0
- Tortoise ORM >= 0.20.0
- pytz

## License

MIT