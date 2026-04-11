# nicegui-rdm: Reactive Data Management

## Why: in a nutshell

ng_rdm offers a clean and modern set of configuration-driven tables with all the plumbing you need to build database-backed CRUD applications with NiceGUI. Moreover, these tables can automatically refresh when back-end data is added or modified. Hence: **reactive** data management. 
 
## Introduction

ng_rdm is based on two ideas:

1. To add **reactivity to database applications**, changes in data should be reflected in UI components, *without* the user having to refresh a page. Imagine a table showing items, counts, stock being updated in near real-time as data is changing. This is the core of the library, implemented in `models` and `store`. Note: this is similar to but *complementary* to standard NiceGUI reactivity (bindings etc; see notes on architecture below). 

2. Secondly, we can move the logic for larger **'composite' UI elements** (such as tables, dialogs, edit cards) from JavaScript/Vue (and Quasar!@&#*?!#)  over to the Python side. In `components/widgets` you'll find tables that create clean html with semantic CSS selectors. And 'as a bonus', because they are on the Python side, it's easy to register them as reactive observers with the stores mentioned above. 

Note that you can use both main parts of the library independently of each other: use the `components` to generate clean html/css widgets, with behavior entirely controlled in Python. Or you can use `store` and `model` as an observer-based back-end for your own reactive user interface (see the vanilla_store example).

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
│  CRUD · validation · observer pattern - EventNotifier    │
└──────────────┬─────────────────────────────────┬─────────┘
               │  2. validate & write            ▲
               ▼                                 │  5. return result
┌──────────────┴─────────────────────────────────┴─────────┐
│  Data Layer                                              │
│  Tortoise ORM · RdmModel / MultitenantRdmModel           │
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

### My first CRUD database app with ng_rdm

```python
from nicegui import app, ui
from tortoise import fields

from ng_rdm import TortoiseStore, init_db, FieldSpec, Validator, store_registry
from ng_rdm.models import RdmModel
from ng_rdm.components import (
    rdm_init, Column, TableConfig, FormConfig,
    ActionButtonTable, EditDialog,
)

# 1. Define a model with validation
class Task(RdmModel):
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

**Multitenancy** — `MultitenantTortoiseStore` and `mt_store_registry`. Models subclass `MultitenantRdmModel` for automatic tenant-field declaration.

Tables and forms are defined through configuration (`TableConfig, Column, FormConfig`). 

See [`components/API.md`](components/API.md) for the full component API.

Q: Why the overlap with existing NiceGUI/Quasar classes, e.g., ui.row/column, ui.dialog, ui.separator? <br>
A: Because Quasar kept sabotaging CSS styling: adding unstyled div layers, lacking dialog size & position control, etc.

## Examples

Run any example with `python -m ng_rdm.examples.<name>`.

| Example | Description |
|---------|-------------|
| `catalog` | Component catalog — showcases all widgets |
| `master_detail` | ViewStack master-detail navigation |
| `multitenant` | MultitenantTortoiseStore — tenant-isolated stores |
| `chips` | Custom cell rendering via `Column.render` — colored status chips |
| `in_row_editing` | Custom `ObservableRdmTable` subclass with inline per-cell editing |
| `custom_datasource` | Build your own store backend |
| `vanilla_store` | Use stores with vanilla NiceGUI components |
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
│   ├── rdm_model.py         — RdmModel (extended Tortoise ORM Model)
│   └── mt_rdm_model.py      — MultitenantRdmModel (tenant-scoped abstract base)
├── components/              — UI components
│   ├── __init__.py          — exports rdm_init(), all components
│   ├── base.py              — ObservableRdmComponent and config helpers
│   ├── protocol.py          — RdmDataSource protocol (structural typing)
│   ├── fields.py            — build_form_field() for forms; build_cell_field() for table cells
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
    ├── master_detail.py     — master-detail pattern with ViewStack
    ├── multitenant.py       — MultitenantTortoiseStore with two tenant stores, quadrant layout
    ├── in_row_editing.py    — custom ObservableRdmTable subclass with inline per-cell editing
    ├── chips.py             — custom cell rendering via Column.render (colored status chips)
    ├── custom_datasource.py — custom RdmDataSource implementation
    ├── vanilla_store.py     — using a store with standard NiceGUI components
    └── topic_filtering.py   — topic-based filtering demo (advanced)
```

## Details

### Multitenancy

For multitenant apps, use the specialized subclasses:
* `MultitenantRdmModel`, which adds the mandatory `tenant` field to `RdmModel`
* `MultitenantTortoiseStore` and `mt_store_registry`, which manage a singleton store instance *per tenant* as well as per type

`tenant` is a varchar(64) so should be able to fit both regular strings (eg, subdomain) and UUIDs. 

```python
## e.g., in your business logic, eg, domain.py
from ng_rdm.models import MultitenantRdmModel, RdmModel

class Product(MultitenantRdmModel):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    # `tenant` is inherited — no need to declare it

    class Meta(RdmModel.Meta):
        table = "products"

## in your global app init, define tenants and register the stores 
from ng_rdm import set_valid_tenants, mt_store_registry
...
@app.on_startup
async def startup():
    tenants = ['acme', 'brutus']
    set_valid_tenants(tenants)
    for t in tenants:
        mt_store_registry.register_store(t, "product", MultitenantTortoiseStore(Product, tenant=t))

## in your page function, get the store and read_items
from ng_rdm import mt_store_registry
    ...
    tenant = 'acme'
    product_store = mt_store_registry.get_store(tenant, "product")
    product_store.read_items(...)

```
Note that the database table name has to be defined in a Meta subclass of `RdmModel.Meta`, not `MultitenantRdmModel`.

See the `multitenant.py` working example, which also shows reactivity *within* tenants and isolation *across* tenants.

### Batching store notifications

By default, atomic store mutations on TortoiseStores are 'de-bounced' by waiting for 100ms before sending notifications to observer components. This is primarily to stabilize the UI if multiple updates are made, but of course it also reduces the load on server and database.

Client code that needs to perform a number of creates or updates in one go should use the batch context manager provided by the store:
```python
    async with store.batch():
        await store.create_item(item1)
        await store.create_item(item2)
    # Single batch event fires here -> batch notification to observers
```

### Topic filtering

By default every observer registered on a store receives every store event (and will typically refresh/rebuild). Topic filtering lets an observer subscribe only to events for items that match a specific field value — for example a UI panel that shows one tenant's data subscribes with `topics={"tenant_id": 42}` and is skipped for all other tenants' events. There is no entry/exit logic: we can't subscribe to 'field X changed'.

Call `store.set_topic_fields(["name", "country"])` once to declare which item fields are eligible for topic filtering by the store. Call `store.add_observer(<callback>, topics={"country": "UK"})` from the page. Multiple keys are AND-ed.

Note that when events are coalesced into a single `"batch"` event (either via debouncing or via context manager), topic matching is bypassed and **all** observers are notified conservatively. It is OK for topic filtering to be a little 'leaky', erroring on the side of the occasional redundant refresh.

See the `topic_filtering.py` example for more details.
 
### Helpers

The library includes a few helpers:

* `utils/logging.py`: call `configure_logging(log_file="app.log", console=True)` once in `main.py` before any other startup code, and all ng_rdm, Tortoise ORM, and uvicorn output goes to that file and/or the console. Without calling it, the library stays silent by default and lets the host app's own logging config take over. Import `from ng_rdm import logger` to write to the same logger in your own app code.

* `components/i18n.py`: self-contained translations for the generic CRUD labels used in components (buttons, confirmations, validation messages). Ships with English (default) and Dutch. Pass `custom_translations` to `rdm_init()` to add a language or override strings; call `set_language('nl_nl')` to switch. Intentionally separate from any app-level i18n to keep the package portable.


### Show refresh via CSS

If you want to see which tables/components are being refreshed, you can pass `show_refresh_transitions = True` to the `rdm_init` call. This adds an animated green border whenever a component is rebuilt &ndash; as in the examples.

### Other restrictions

The way we use Tortoise ORM assumes every table has an integer primary key called `id`. It's possible that things will work if you do it differently, but it's quite likely something will break.

## Some notes on architecture

### About "front-end" vs "back-end" reactivity

This library has evolved from discussions on the NiceGUI repo going back to 2023, e.g. [#1042](https://github.com/zauberzeug/nicegui/discussions/1042), [#4172](https://github.com/zauberzeug/nicegui/discussions/4172). Recently an interesting discussion around [reaktiv](https://github.com/zauberzeug/nicegui/discussions/4758) gives some pointers where reactivity might be going.

In ng_rdm, the focus is on **adding reactivity to structurally persistent and shared data/state** - what was traditionally called the 'back-end'. It is kept separate from transient and user-specific state ('front-end?'), where reactivity can be provided by NiceGUI bindings and other Vue/Quasar mechanisms. 

In ng_rdm, when data is changed, the component's `@ui.refresh` is called: this then requests a fresh copy of the data from the store and rebuilds the UI (eg, a table). For components with meaningful 'user' state, a `state` dict is passed to the component's constructor. This dict is kept in the page context, *outside* of the component itself. That 'user' state is re-applied when the component is rebuilt. Selected rows remain selected, checkboxes and radio buttons remain unchanged.

A useful pattern (see the examples) is to instantiate for every page an overall `ui_state` dict that represents the "user state" and can be persisted in `app.storage.user`.  A dict within `ui_state` is then passed on to ng_rdm components (or other `@ui.refreshables`) as their local 'user state'. 


### What a store does and does not do

While Tortoise is nominally an ORM, it is used here more as a basic data access layer. `RdmModel` in `models` adds extended field definitions, field level validators/normalizers and join_field logic to navigate foreign-key relationships. The `store` layer on top of Tortoise is the core of the library and also performs some functions typically delegated to an ORM.

What a store *does* do:
* it maps a single database table (including related data) to a set of business objects
* it provides a basic set of CRUD functions to read and write data...
* ... using [lists of] dictionaries as the representation format
* it notifies registered observers of changes to the store, eg create, update, delete
* it performs validation and normalization (via RdmModel)
* it offers (de-)hydration functions to translate database representation to business space and vice versa (e.g., dates, datetimes, NULL)

What a store does *not* do:
* it does not do any caching: all read_items(...) etc. go straight to the database via Tortoise
* it has limited understanding of relations in the data model: a store is centered on a single database table, with some options to query related tables ('join_fields')
* it is not intended to scale: an app will usually have a *single instance* for every type of store (see `store_registry` in `store/base.py`) to allow the store to distribute incoming changes to the relevant observers

### Directions / improvements

* For tables specifically: (a) adding search/filtering to tables, both the chrome and the query logic and (b) adding standard 'Load more...' logic, to extend the number of rows in scope for a table.

* It would be very interesting to investigate if the observer/event mechanisms now exposed by `ng_rdm.store` can be based on the binding mechanisms and/or (perhaps more feasible) on reaktiv/Signals.

* Currently with topic filtering we have a limited tool to influence *whether* or not to refresh a component. But when triggered, the *entire component* is always rebuilt. That is due to the `StatefulRefreshable` pattern that we started out with. It would be wild to move 'closer to the DOM', as it were and to selectively patch the cells that needed patching. 

* Related to this: currently `@ui.refreshable` is doing all the heavy lifting. At some point it may be better to isolate the actual DOM operations and tie them more closely to the event logic (and perhaps, a generic Signals type architecture). 

### Caution: scalability

This library is absolutely **not** intended or suitable for applications with thousands of concurrent users, at least not for fully reactive UI's: a single update of a database table will lead to multiple reads *per connected client* (refresh -> reread). The typical use case is for dashboard-type apps that have a handful of users; without actually testing it, I'd estimate a practical upper limit to be around ~50-100 concurrent users?

Note that by default, all table classes register as observers to the stores they depend on, for all events. The first step to improve scalability is to set `auto_observe=False` when instantiating the component &ndash; and then to either register your observer with topic filtering or even better, don't register it at all if you don't need reactivity.

## Requirements

- Python 3.12+
- NiceGUI >= 1.4.0
- Tortoise ORM >= 0.20.0
- pytz

## License

MIT