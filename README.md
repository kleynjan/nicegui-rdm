# nicegui-rdm: Reactive Data Management

## Why: in a nutshell

ng_rdm offers a clean and modern set of (non-Quasar) tables with all the plumbing you need to build database-backed NiceGUI applications. Moreover, these tables can automatically refresh when back-end data is added or modified. Hence: **reactive** data management. 
 
## Introduction

ng_rdm is based on two ideas:

1. To add **reactivity to database applications**, changes in data should be reflected in UI components, *without* the user having to refresh a page. Imagine a table showing items, counts, stock being updated in near real-time as data is changing. This is the core of the library, implemented in `models` and `store`. Note: this is similar to but *complementary* to the reactivity we can easily achieve &lsquo;client-side&rsquo; with  NiceGUI bindings etc. 

2. Secondly, NiceGUI's websocket architecture allows us to move the logic for larger **'composite' UI elements** (such as tables, dialogs, edit cards) from JavaScript/Vue (and Quasar!@&#*?!#)  over to the Python side. In `components/widgets` you'll find tables that create clean html with semantic CSS selectors. And 'as a bonus', because they are on the Python side, it's easy to register them as reactive observers with the stores mentioned above. 

Note that you can use the main parts of the library independently of each other: you can use the `components` to generate clean html/css widgets, with behavior entirely controlled in Python. And you can use `store` and `model` as an observer-based back-end for your own reactive user interface (see the vanilla_store example).

## Library overview

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


## Quick start

### Installation

```bash
pip install nicegui-rdm
import ng_rdm   # import path differs from package name
```

### My first app

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
    rdm_init()  # initialize ng_rdm - required for every page

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

Run any example with `python -m ng_rdm.examples.<name>`.

| Example | Description |
|---------|-------------|
| `catalog` | Component catalog — showcases all widgets |
| `master_detail` | ViewStack master-detail navigation |
| `multitenant` | MultitenantTortoiseStore — tenant-isolated stores |
| `custom_datasource` | Custom `RdmDataSource` implementation |
| `vanilla_store` | Basic store usage without ng_rdm components |
| `topic_filtering` | Topic-based observer filtering |

## Working with ng_rdm

### App organization

One pattern to consider is to create a `domain` or `app_logic` directory and to add your app-specific logic there. That's a good place to add an app-specific `models.py` and `stores.py`  

You will often need or want to extend a generic `TortoiseStore` or `MultitenantTortoiseStore` for a specific model with more business logic, overriding methods like `read_items` or `_update_item`. A typical class definition in `domain/stores.py` might look like this: <br>`class EnrichedProductStore(MultitenantTortoiseStore[Product]):...`
Along the same lines, `domain/models.py` would be a good place to put `Qmodel` subclasses: `class Product(QModel):...` (also see examples).

### Helpers

The library includes a few helpers:

* `utils/logging.py`: pass `log_file="app.log"` to `rdm_init()` and all ng_rdm, Tortoise ORM, and uvicorn output goes to that file — nothing else to configure. Without a path, the library stays silent and lets the host app's logging config take over. You can also do `from ng_rdm import logger` to write to the same logger in your own app code.

* `components/i18n.py`: self-contained translations for the generic CRUD labels used in components (buttons, confirmations, validation messages). Ships with English (default) and Dutch. Pass `custom_translations` to `rdm_init()` to add a language or override strings; call `set_language('nl_nl')` to switch. Intentionally separate from any app-level i18n to keep the package portable.

### Show refresh via CSS

If you want to see which tables/components are being refreshed, you can pass `show_refresh_transitions` = True to the `rdm_init` call. If enabled, it adds an animated green border whenever a component is rebuilt &ndash; as in the examples.

## Some notes on architecture

### About "front-end" vs "back-end" reactivity

A starting point for this library has been to provide reactivity for structurally persistent and shared ('back-end'?) data state, but to keep it separate from more transient and user-specific ('client?') state, where reactivity can be provided for instance by NiceGUI bindings. 

When data is changed, the component's `@ui.refresh` is called: it requests a fresh copy of the data from the store and rebuilds the UI. Meanwhile, the user state ('client state'?) is kept in a dict passed to the constructor, so *outside* of the component itself - and that state is re-applied when the component is rebuilt. Selected rows remain selected, checkboxes and radio buttons remain unchanged.

A useful pattern (see the examples) is to instantiate for every page an overall `ui_state` dict that represents the "user state" and can be persisted in `app.storage.user`.  A dict within `ui_state` is then passed on to ng_rdm components (or other `@ui.refreshables`) as their local 'user state'. 

See NiceGUI discussions going back to 2023 if you want more background, e.g. [#1042](https://github.com/zauberzeug/nicegui/discussions/1042), [#4172](https://github.com/zauberzeug/nicegui/discussions/4172) and more recently an interesting discussion around [reaktiv](https://github.com/zauberzeug/nicegui/discussions/4758).

### What a store does and does not do

While Tortoise is nominally an ORM, it is used here more as a basic data access layer. `Qmodel` in `models` adds extended field definitions, field level validators/normalizers and join_field logic to navigate foreign-key relationships. The `store` layer on top of Tortoise is the core of the library and performs some ORM-like functions.

What a store *does* do:
* it maps a single database table (including related data) to a set of business objects
* it provides a basic set of CRUD functions to read and write data...
* ... using [lists of] dictionaries as the representation format
* it notifies registered observers of changes to the store, eg create, update, delete
* it performs validation and normalization (via Qmodel)
* it offers (de-)hydration functions to translate database representation to business space and vice versa (e.g., dates, datetimes, NULL)

What a store does *not* do:
* it does not do any caching: all read_items(...) etc. go straight to the database via Tortoise
* it has limited understanding of relations in the data model: a store is centered on a single database table, with some options to query related tables ('join_fields')
* it is not intended to scale: an app will usually have a *single instance* for every type of store (see `store_registry` in `store/base.py`) to allow the store to distribute incoming changes to the relevant observers; (but note: if you use the multitencancy pattern, there will be one instance per type, *per tenant*)

### Directions / improvements

* It would be very interesting to investigate if the observer/event mechanisms now exposed by `ng_rdm.store` can be based on the binding mechanisms and/or (perhaps more feasible) on reaktiv/Signals.

* Currently we have some tools to influence *whether* or not to refresh a component (e.g., subscribing to `topics`), but when triggered, we always rebuild the entire component. That is due to the `StatefulRefreshable` pattern that we started out with. It would be wild to move 'closer to the DOM', as it were and to selectively patch the cells that needed patching. 

* Related to this, `@ui.refreshable` is doing a lot of heavy lifting and it would perhaps be better to isolate the actual DOM operations and tie them more closely to the event logic. Again, this is due to where we started with this library years ago. 

### Caution: scalability

This library is absolutely **not** intended or suitable for applications with thousands of concurrent users, at least not for fully reactive UI's: a single update of a database table will lead to multiple reads *per connected client* (refresh -> reread). The typical use case is for dashboard-type apps that have a handful of users; without actually testing it, I'd estimate the upper limit to be around 50-100 concurrent users. 

Note that by default, all table classes register as observers to the stores they use. The first step to scalability is to set `auto_observe` to False when instantiating an `ObservableRdmTable` or descendant and you don't need the reactivity. 

## Requirements

- Python 3.12+
- NiceGUI >= 1.4.0
- Tortoise ORM >= 0.20.0
- pytz

## License

MIT