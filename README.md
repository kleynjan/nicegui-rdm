# nicegui-rdm: Reactive Data Management

## Why: in a nutshell

ng_rdm offers a clean and modern set of (non-Quasar) tables with all the plumbing you need to build database-backed NiceGUI applications. Moreover, these tables can automatically refresh when back-end data is added or modified. Hence: **reactive** data management. 
 
## Background (feel free to skip)

ng_rdm is based on two ideas:

1. For my own apps I needed to add **reactivity to database applications**: changes in data should be reflected in UI components, *without* the user having to refresh a page. Imagine a table showing items, counts, stock being updated in near real-time as data is changing. This is the core of the library, implemented in `models` and `store`. Note: this is similar to but *complementary* to the reactivity we can easily achieve &lsquo;client-side&rsquo; with  NiceGUI bindings etc. 

2. Secondly, I've always been fighting Quasar's **&ldquo;composite&rdquo; UI components** such as tables, dialogs, cards, etc.: layer upon layer of div's and the most obnoxious CSS imaginable. Thanks to NiceGUI's websocket architecture we can move the logic for and behavior of those components from JavaScript/VueJS over to the Python side. In `components/widgets` you'll find tables that create clean html with semantic CSS selectors and that tie in to `store` observability &ndash; entirely in Python. 

See below for a more detailed overview of the architecture.


## Installation

```bash
pip install nicegui-rdm
```

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  UI Components                                           │
│  ActionButtonTable · ListTable · SelectionTable          │
│  EditDialog · EditCard · DetailCard · ViewStack          │
└──────────────┬─────────────────────────────────┬─────────┘
               │  1. user action                 ▲
               ▼                                 │  6. notify_observers
┌──────────────┴─────────────────────────────────┴─────────┐
│  Store Layer                                             │
│  Store (base) · DictStore · TortoiseStore                │
│  MultitenantTortoiseStore · StoreRegistry                │
│  CRUD · validation · observer pattern                    │
└──────────────┬─────────────────────────────────┬─────────┘
               │  2. validate & write            ▲
               ▼                                 │  5. return result
┌──────────────┴─────────────────────────────────┴─────────┐
│  Data Layer                                              │
│  Tortoise ORM · QModel                                   │
│  SQLite · PostgreSQL · MySQL                             │
└──────────────────────────────────────────────────────────┘
```

User actions flow **down** through the Store layer (which validates and normalizes) to the database. On success, the Store broadcasts a `StoreEvent` **up** to all subscribed UI components, which automatically rebuild via `@ui.refreshable_method`. This is the reactive loop that keeps tables and detail views in sync with the database without manual refresh.

## Quick Start

```python
from nicegui import app, ui
from tortoise import fields

from ng_rdm import TortoiseStore, init_db, close_db, FieldSpec, Validator
from ng_rdm.models import QModel
from ng_rdm.components import (
    rdm_init, Column, TableConfig, FormConfig,
    ActionButtonTable, EditDialog,
)

# 1. Define a model with validation
class Task(QModel):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)

    field_specs = {
        "name": FieldSpec(validators=[
            Validator("Name is required", lambda v, _: bool(v and v.strip()))
        ])
    }

# 2. Initialize database and create a store (module level)
init_db(app, "sqlite://tasks.db", modules={"models": [__name__]}, generate_schemas=True)
app.on_shutdown(close_db)

task_store = TortoiseStore(Task)

# 3. Build a page
@ui.page("/")
async def index():
    rdm_init()  # load CSS + Bootstrap Icons

    columns = [Column("name", "Task name")]
    table_config = TableConfig(columns=columns)
    form_config = FormConfig(columns=columns, title_add="New Task", title_edit="Edit Task")

    # EditDialog for add/edit; ActionButtonTable for display
    dlg = EditDialog(data_source=task_store, config=form_config,
                     on_saved=lambda _: table.build.refresh())
    table = ActionButtonTable(
        data_source=task_store, config=table_config,
        on_add=dlg.open_for_new, on_edit=dlg.open_for_edit,
    )
    await table.build()

ui.run()
```

## What's Included

**Tables** — `ActionButtonTable` (CRUD with per-row action buttons), `ListTable` (read-only clickable rows), `SelectionTable` (checkbox multi-select)

**Forms** — `EditDialog` (modal create/edit), `EditCard` (inline form)

**Navigation** — `ViewStack` (list/detail/edit flow), `Tabs` (tabbed content)

**Display** — `DetailCard` (read-only detail view), `Dialog` (modal overlay), `StepWizard` (multi-step form)

**Layout** — `Button`, `IconButton`, `Icon`, `Row`, `Col`, `Separator`

**Store layer** — `DictStore` (in-memory), `TortoiseStore` (ORM-backed), `MultitenantTortoiseStore` (tenant-scoped)

See [`components/API.md`](components/API.md) for the full component API reference.

## Examples

Run any example with `python -m ng_rdm.examples.<name>` and open http://localhost:8080.

| Example | Description |
|---------|-------------|
| `catalog` | Component catalog — showcases all widgets |
| `master_detail` | ViewStack master-detail navigation |
| `custom_datasource` | Custom `RdmDataSource` implementation |
| `vanilla_store` | Basic store usage without UI components |
| `topic_filtering` | Topic-based observer filtering |

## Requirements

- Python 3.12+
- NiceGUI >= 1.4.0
- Tortoise ORM >= 0.20.0
- pytz

## License

MIT