# ng_loba

Line of Business Application components for NiceGUI.

## Overview

ng_loba provides a collection of reusable components for building line-of-business applications with NiceGUI:

- **Store**: State management with validation and observer pattern
  - Base Store with CRUD operations
  - DictStore for in-memory storage
  - TortoiseStore for ORM-based storage
  
- **Refreshable**: Reactive UI components
  - StatefulRefreshable for state-based UI updates
  - StoreRefreshable for store-based UI updates
  
- **CRUD**: Data management components
  - CrudTable for editable data tables
  - Support for validation, sorting, and keyboard navigation
  
- **Utils**: Common utilities
  - Field validation and normalization
  - Logging configuration

## Installation

For development (editable mode):
```bash
pip install -e .
```

With development dependencies:
```bash
pip install -e ".[dev]"
```

## Usage

### Store Example

```python
from ng_loba import Store, Validator, FieldSpec

# Define field validation
name_validator = Validator(
    message="Name must not be empty",
    validator=lambda v, _: bool(v.strip())
)

# Create store with validation
store = Store({
    'name': FieldSpec(validators=[name_validator])
})

# Use CRUD operations
await store.create_item({'name': 'Test'})
items = await store.read_items()
```

### CrudTable Example

```python
from ng_loba import CrudTable, Column, TableConfig
from nicegui import ui

# Define table columns
config = TableConfig(
    columns=[
        Column(name='name', label='Name', ui_type=ui.input),
        Column(name='email', label='Email', ui_type=ui.input),
    ],
    focus_column='name'
)

# Create table
table = CrudTable(
    state={'editor': {}},
    store=store,
    config=config
)

# Build table in UI
await table.build()
```

### Refreshable Example

```python
from ng_loba import StoreRefreshable

class UserList(StoreRefreshable):
    async def _rebuild(self):
        items = await self.store.read_items()
        with ui.column():
            for item in items:
                ui.label(item['name'])

# Create and build component
user_list = UserList(state={}, store=store)
await user_list.build()
```

## Development

Run tests:
```bash
pytest
```

## License

MIT
