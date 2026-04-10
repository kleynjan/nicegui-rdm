# nicegui-rdm: Reactive Data Management

## Why: in a nutshell

ng_rdm offers a clean and modern set of configuration-driven tables with all the plumbing you need to build database-backed CRUD applications with NiceGUI. Moreover, these tables can automatically refresh when back-end data is added or modified. Hence: **reactive** data management. 
 
## Introduction

ng_rdm is based on two ideas:

1. To add **reactivity to database applications**, changes in data should be reflected in UI components, *without* the user having to refresh a page. Imagine a table showing items, counts, stock being updated in near real-time as data is changing. This is the core of the library, implemented in `models` and `store`. Note: this is similar to but *complementary* to standard NiceGUI reactivity (bindings etc; see notes on architecture below). 

2. Secondly, we can move the logic for larger **'composite' UI elements** (such as tables, dialogs, edit cards) from JavaScript/Vue (and Quasar!@&#*?!#)  over to the Python side. In `components/widgets` you'll find tables that create clean html with semantic CSS selectors. And 'as a bonus', because they are on the Python side, it's easy to register them as reactive observers with the stores mentioned above. 

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
│  Store (base) · DictStore · (Multitenant)TortoiseStore   │
│  (Multitenant)StoreRegistry                              │
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

from ng_rdm import TortoiseStore, init_db, FieldSpec, Validator, store_registry
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

# 2. Initialize database
init_db(app, "sqlite://tasks.db", modules={"models": [__name__]}, generate_schemas=True)

# 3. Create a store and add it to the registry singleton
store_registry.register_store("task", TortoiseStore(Task))

# 4. Build a page
@ui.page("/")
async def index():

    # 4a. Initialize ng_dm - required for every page
    rdm_init()

    # 4b. Get the stores you need from the registry
    task_store = store_registry.get_store("task")

    # 4c. Configure the table and form
    columns = [Column("name", "Task name")]
    table_config = TableConfig(columns=columns)
    form_config = FormConfig(columns=columns, title_add="New Task", title_edit="Edit Task")

    # 4d. Create the table & edit components
    dlg = EditDialog(data_source=task_store, config=form_config)

    table = ActionButtonTable(
        # note: the `auto_observe` is default, so the table is refreshed when store data updates
        data_source=task_store, config=table_config,
        on_add=dlg.open_for_new, on_edit=dlg.open_for_edit,
    )
    await table.build()

ui.run()
```

In practice you will often want subclass generic stores to enhance/override `_read_items` or `_update_item` methods. Eg, `class EnrichedTaskStore(TortoiseStore[Task]):...`

## What's Included

**Tables** — `ActionButtonTable` (CRUD with per-row action buttons), `ListTable` (read-only clickable rows), `SelectionTable` (checkbox multi-select)

**Forms** — `EditDialog` (modal create/edit), `EditCard` (inline form)

**Navigation** — `ViewStack` (master/detail/edit flow), `Tabs` (tabbed content)

**Display** — `DetailCard` (read-only detail view), `Dialog` (modal overlay), `StepWizard` (multi-step form)

**Layout** — `Button`, `IconButton`, `Icon`, `Row`, `Col`, `Separator`

**Store layer** — `DictStore` (in-memory), `TortoiseStore` (ORM-backed), `store_registry`

**Multitenancy** -  `MultitenantTortoiseStore` and `mt_store_registry`

Tables and forms are defined through configuration (`TableConfig, Column, FormConfig`). See [`components/API.md`](components/API.md) for the full component API.

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

## Project structure

```
src/ng_rdm/
├── __init__.py              — package root (exports Store layer)
├── store/                   — state management & data layer
│   ├── base.py              — Store (add/remove_observer, set_topic_fields), StoreRegistry, store_registry
│   ├── dict_store.py        — DictStore (in-memory store)
│   ├── orm.py               — TortoiseStore (Tortoise ORM integration)
│   ├── multitenancy.py      — MultitenantTortoiseStore, MultitenantStoreRegistry, mt_store_registry
│   └── notifier.py          — EventNotifier (batching, debouncing, topic filtering), StoreEvent
├── models/                  — data model helpers
│   ├── types.py             — Validator, FieldSpec NamedTuples
│   └── qmodel.py            — QModel (extended Tortoise ORM Model)
├── components/              — UI components
│   ├── __init__.py          — exports rdm_init(), all components
│   ├── base.py              — ObservableRdmComponent and config helpers
│   ├── protocol.py          — RdmDataSource protocol (structural typing)
│   ├── fields.py            — build_form_field() shared utility
│   ├── i18n.py              — localization (currently Dutch/English, easily expandable)
│   ├── ng_rdm.css           — design system stylesheet
│   └── widgets/             — concrete UI widget components
│       ├── action_button_table.py — ActionButtonTable (table with per-row action buttons)
│       ├── list_table.py    — ListTable (read-only with clickable rows)
│       ├── selection_table.py — SelectionTable (checkbox multi-select)
│       ├── dialog.py        — Dialog (positioned card overlay)
│       ├── detail_card.py   — DetailCard (read-only detail view)
│       ├── edit_card.py     — EditCard (in-place editing form, takes FormConfig)
│       ├── edit_dialog.py   — EditDialog (modal editing dialog, takes FormConfig)
│       ├── tabs.py          — Tabs (div-based tab switcher)
│       ├── view_stack.py    — ViewStack (navigation coordinator with render slots)
│       ├── wizard.py        — StepWizard, WizardStep (multi-step form wizard)
│       ├── button.py        — Button, IconButton, Icon
│       └── layout.py        — RdmLayoutElement, Row, Col, Separator
├── utils/                   — utilities
│   ├── helpers.py           — date/time, validation, formatting
│   └── logging.py           — logger setup & configuration
├── debug/                   — developer tooling
│   ├── event_log.py         — EventLog (rotating buffer), EventLogEntry, event_log singleton
│   └── page.py              — enable_debug_page() registers /rdm-debug route
└── examples/
    ├── catalog.py           — component catalog / showcase
    ├── custom_datasource.py — custom RdmDataSource implementation
    ├── master_detail.py     — master-detail pattern with ViewStack
    ├── vanilla_store.py     — basic store usage without components
    ├── topic_filtering.py   — topic-based filtering demo
    └── multitenant.py       — MultitenantTortoiseStore with two tenant stores, quadrant layout
```

## Working with ng_rdm

### Helpers

The library includes a few helpers:

* `utils/logging.py`: call `configure_logging(log_file="app.log", console=True)` once in `main.py` before any other startup code, and all ng_rdm, Tortoise ORM, and uvicorn output goes to that file and/or the console. Without calling it, the library stays silent by default and lets the host app's own logging config take over. Import `from ng_rdm import logger` to write to the same logger in your own app code.

* `components/i18n.py`: self-contained translations for the generic CRUD labels used in components (buttons, confirmations, validation messages). Ships with English (default) and Dutch. Pass `custom_translations` to `rdm_init()` to add a language or override strings; call `set_language('nl_nl')` to switch. Intentionally separate from any app-level i18n to keep the package portable.

### Multitenancy

For multitenant apps, use 
use `MultitenantTortoiseStore` together with `mt_store_registry` (a `MultitenantStoreRegistry` instance in `store/multitenancy.py`). The registry keys stores by `(tenant, name)`:

```python
from ng_rdm import mt_store_registry as store_registry  # alias keeps call-sites unchanged

store_registry.register_store("acme", "products", MultitenantTortoiseStore(Product, tenant="acme"))
store = store_registry.get_store("acme", "products")
```

### Show refresh via CSS

If you want to see which tables/components are being refreshed, you can pass `show_refresh_transitions` = True to the `rdm_init` call. If enabled, it adds an animated green border whenever a component is rebuilt &ndash; as in the examples.

### Other restrictions

The way we use Tortoise ORM assumes every table has an integer primary key called `id`. It's quite possible that things will work if you do it differently, but it's quite likely something will break.

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
* it is not intended to scale: an app will usually have a *single instance* for every type of store (see `store_registry` in `store/base.py`) to allow the store to distribute incoming changes to the relevant observers


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