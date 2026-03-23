# ng_store Examples

This directory contains runnable examples demonstrating the ng_store library.

## Directory Structure

```
examples/
├── store/              # Store-only examples (no UI dependencies)
│   ├── dict_store.py   # In-memory CRUD with validation and observers
│   ├── tortoise_store.py  # SQLite-backed CRUD with ORM models
│   └── multitenancy.py # Tenant-scoped store operations
│
└── components/         # UI component examples (requires NiceGUI)
    ├── custom_table.py # Build your own table using StoreComponent
    ├── org_demo.py     # ViewStack master-detail navigation
    └── showcase.py     # Comprehensive component tutorial
```

## Running Examples

All examples use module syntax from the project root:

### Store Examples (Pure Python)

These run without a web server and demonstrate core store functionality:

```bash
python -m ng_store.examples.store.dict_store      # In-memory CRUD, validation
python -m ng_store.examples.store.tortoise_store  # SQLite database, ORM
python -m ng_store.examples.store.multitenancy    # Tenant-scoped operations
```

### Component Examples (NiceGUI)

These start a web server - open http://localhost:8080 in your browser:

```bash
python -m ng_store.examples.components.showcase      # Component tutorial
python -m ng_store.examples.components.custom_table  # Custom table component
python -m ng_store.examples.components.org_demo      # ViewStack hierarchical data
```

## Key Concepts

### Store Examples

- **DictStore**: In-memory dictionary-based store for quick prototyping
- **TortoiseStore**: ORM-backed store with SQLite/PostgreSQL support
- **MultitenantTortoiseStore**: Tenant-scoped data isolation
- **FieldSpec & Validator**: Input validation and normalization
- **Observer pattern**: Automatic UI refresh on data changes

### Component Examples

- **DataTable**: Editable table with modal add/edit dialogs
- **ListTable**: Read-only clickable rows for navigation
- **SelectionTable**: Multi-select with checkboxes
- **ViewStack**: List → detail → edit navigation pattern
- **Dialog**: Modal overlay
- **Tabs**: Tab-based content switching
- **StoreComponent**: Base class for custom store-connected components

## API Quick Reference

### Store

```python
from ng_store.store import DictStore, TortoiseStore, init_db, close_db
from ng_store.models import QModel, FieldSpec, Validator

# Create store
store = DictStore(field_specs={...})
store = TortoiseStore(MyModel)

# CRUD operations (all async)
item = await store.create_item({...})
items = await store.read_items(filter_by={...})
updated = await store.update_item(id, {...})
await store.delete_item(item)

# Observer pattern
store.add_observer(lambda event: print(event.verb, event.item))
```

### Components

```python
from ng_store.components import (
    crud_init,       # Initialize CSS/icons
    DataTable,       # Editable table with modal dialog
    ListTable,       # Read-only clickable rows
    SelectionTable,  # Multi-select with checkboxes
    ViewStack,       # Master-detail navigation
    Dialog,          # Modal overlay
    Tabs,            # Tab switcher
)
```
