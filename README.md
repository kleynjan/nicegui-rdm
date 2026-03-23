# nicegui-rdm

Reactive Database Management for NiceGUI applications with Tortoise ORM.

## Overview

nicegui-rdm provides a reactive state management layer that bridges Tortoise ORM and NiceGUI:

- **Store Layer** — Observer pattern for database-backed state with automatic UI refresh
- **Reactive Components** — Tables, dialogs, forms that auto-update on data changes
- **Model Helpers** — Validation, field specs, and extended Tortoise ORM base class
- **Multi-tenancy** — Built-in tenant scoping for SaaS applications

## Installation

```bash
pip install nicegui-rdm
```

## Quick Start

```python
from nicegui import ui
from ng_rdm import DictStore, FieldSpec, Validator
from ng_rdm.components import rdm_init, DataTable, Column, TableConfig

# Define validation
name_validator = Validator(
    message="Name cannot be empty",
    validator=lambda v, _: bool(v.strip()) if v else False
)

# Create a store with field specs
store = DictStore({'name': FieldSpec(validators=[name_validator])})

@ui.page('/')
async def main():
    rdm_init()  # Load styles and icons
    
    # Configure table
    config = TableConfig(
        table_columns=[Column('name', 'Name')],
        dialog_columns=[Column('name', 'Name', required=True)],
    )
    
    # Create reactive table - auto-refreshes on data changes
    table = DataTable({}, store, config)
    await table.build()

ui.run()
```

## Architecture

```mermaid

flowchart BT
    subgraph UI["🖥️ UI Components"]
        direction LR
        UI_DESC["@ui.refreshable build functions<br/>Auto-rebuild on store events<br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"]
    end
    subgraph STORE["📦 Store Layer"]
        direction TB
        STORE_DESC["<b>Denormalized Business Objects</b><br/><small>CRUD interface · Validation · Observer pattern</small>"]
        STORE_COMP["Store <i>(base)</i> · DictStore <i>(memory)</i><br/>TortoiseStore · MultitenantTortoiseStore"]
    end

    subgraph ORM["🔄 ORM Layer"]
        direction TB
        ORM_DESC["<b>Tortoise ORM</b><br/><small>Async Python ORM · Model definitions</small>"]
        ORM_COMP["QModel <i>(extended Model with validation)</i>"]
    end

    subgraph DB["🗄️ Database"]
        direction LR
        SQLITE[(SQLite)]
        POSTGRES[(PostgreSQL)]
        MYSQL[(MySQL)]
    end

    %% Main data flow (mutations) - arrows point down
    UI -->|"1. User action"| STORE
    STORE -->|"2. Validate & normalize"| ORM
    ORM -->|"3. SQL queries"| DB

    %% Reactive flow (notifications) - arrows point up
    DB -.->|"<b>4.</b> Commit success"| ORM
    ORM -.->|"<b>5.</b> Return result"| STORE
    STORE -.->|"<b>6.</b> notify_observers(StoreEvent)<br/><small>Broadcasts to all subscribers</small>"| UI

```

<!-- 
    %% Styling
    style UI fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style STORE fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    style ORM fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style DB fill:#fce4ec,stroke:#c2185b,stroke-width:2px

  themeVariables:
    primaryColor: '#BB2528'
    primaryTextColor: '#fff'
    primaryBorderColor: '#7C0000'
    lineColor: '#F8B229'
    secondaryColor: '#006100'
    tertiaryColor: '#fff'

-->
**Data Flow:** User actions flow down through the Store layer (which validates and normalizes) to the database. On success, the Store broadcasts a `StoreEvent` to all subscribed UI components, which automatically rebuild via `@ui.refreshable`.

## Store Types

### DictStore

In-memory store for prototyping and testing:

```python
from ng_rdm import DictStore, FieldSpec, Validator

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
from ng_rdm import TortoiseStore, init_db
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
from ng_rdm import MultitenantTortoiseStore

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

## Components

### DataTable

Primary editable table with configurable actions:

```python
from ng_rdm.components import DataTable, Column, TableConfig

config = TableConfig(
    table_columns=[
        Column('name', 'Name'),
        Column('email', 'Email'),
    ],
    dialog_columns=[
        Column('name', 'Name', required=True),
        Column('email', 'Email'),
    ],
)

table = DataTable({}, store, config)
await table.build()
```

### ListTable

Read-only table with clickable rows:

```python
from ng_rdm.components import ListTable

table = ListTable({}, store, config, on_click=lambda item: show_detail(item))
await table.build()
```

### ViewStack

List → Detail → Edit navigation:

```python
from ng_rdm.components import ViewStack

stack = ViewStack({}, store, config)
await stack.build()
```

## Observer Pattern

Stores notify observers on any change:

```python
from ng_rdm import StoreEvent

async def on_change(event: StoreEvent):
    print(f"{event.verb}: {event.item}")

store.add_observer(on_change)
```

## Validation

Define field validators and normalizers:

```python
from ng_rdm import FieldSpec, Validator

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

## Requirements

- Python 3.12+
- NiceGUI >= 1.4.0
- Tortoise ORM >= 0.20.0
- pytz

## License

MIT