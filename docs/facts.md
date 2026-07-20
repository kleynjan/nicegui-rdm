# System Facts: ng_rdm Reactive Data Management

## Purpose

ng_rdm (nicegui-rdm on pypi) is a reusable library providing Reactive Database Management for NiceGUI applications. It provides the state management layer, reactive UI components, and model helpers that bridge Tortoise ORM and NiceGUI.

## Architecture

### Layered Design

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

The origins of this project go back to 2023: see for instance NiceGUI Discussions [#1042](https://github.com/zauberzeug/nicegui/discussions/1042) and [#4172](https://github.com/zauberzeug/nicegui/discussions/4172). More recently there have been [interesting discussions](https://github.com/zauberzeug/nicegui/discussions/4758) around reaktiv, Signals and proxying the native NiceGUI reactivity layer &ndash; but as of this moment it's primarily `@ui.refreshable` that's doing the heavy lifting. 

### Data Flow

```
User action → RDM component calls data_source.update_item()
  → TortoiseStore validates (FieldSpec), updates DB
  → Store.notify_observers(StoreEvent)
  → ObservableRdmComponent._handle_datasource_change() triggers build.refresh()
  → @ui.refreshable_method rebuilds UI with new data
```

## Key Design Patterns

### Observer Pattern
Stores maintain a list of observers with optional topic-based filtering. On any create/update/delete, relevant observers are notified via `StoreEvent(verb, item)`. UI components can:
- **Auto-observe** (table components): `ObservableRdmTable` calls `observe(topics=filter_by)` in constructor when `auto_observe=True` (default)
- **Explicit observe**: Set `auto_observe=False` or use `ObservableRdmComponent` directly and call `observe()`/`unobserve()`/`reobserve()` at page level

Topic filtering reduces unnecessary refreshes — observers only receive events matching their subscribed field values.

### Protocol-Based Design
`RdmDataSource` is a Protocol (structural typing), not an abstract base class. Any object implementing `create_item()`, `read_items()`, `update_item()`, `delete_item()`, `validate()`, `add_observer()`, and `remove_observer()` works as a data source — Store, REST API wrapper, mock, etc.

### Validation Pipeline
- `FieldSpec` defines validators (list of `Validator` named tuples) and an optional normalizer per field
- `RdmModel.get_all_field_specs()` merges explicit field specs with auto-generated required-field validators
- `Store.validate()` runs all validators before any write operation
- UI layer shows validation errors via `ui.notify()`

### UI State Pattern

Every component that has front-end state (current view, selection, open/closed, form values) exposes that state through a `state: dict | None = None` parameter (defaults to `{}`). The calling page typically owns and persists this dict; the component only holds a reference.

**Page side** — create a `ui_state` dict per page, backed by `app.storage.user` for persistence across NiceGUI's server-side refreshes, and pass sub-dicts to each component:

```python
app.storage.user["ui_state"] = {
    "tabs":      {"active": "products"},   # set initial state here
    "viewstack": {},
    "selection": {},
    "dialog":    {},
}
ui_state = app.storage.user["ui_state"]

tabs = Tabs(state=ui_state["tabs"], tabs=[...])
stack = ViewStack(state=ui_state["viewstack"], ...)
```

**Component side** — use `setdefault()` to fill in missing keys without overwriting caller-supplied values:

```python
def __init__(self, state: dict, ...):
    self.state = state
    self.state.setdefault("active", self.tabs[0][0])
```

**Why `app.storage.user`:** NiceGUI's `@ui.refreshable` tears down and rebuilds DOM subtrees on store events. Because the component only holds a reference to the dict (not a copy), the rebuilt component finds the same dict in `self.state` with unchanged keys — so the current navigation mode, tab, or selection is automatically preserved after a store-triggered rebuild.

**NiceGUI bindings on the state dict** — bind UI elements directly to state keys for reactive updates that don't require a full DOM rebuild:

```python
# Visibility driven by state (Tabs, ViewStack)
panel.bind_visibility_from(self.state, "active", backward=lambda v, k=key: v == k)

# Label text driven by state (SelectionTable selection count)
label.bind_text_from(ui_state["selection"], "selected_ids",
                     backward=lambda ids: f"{len(ids)} selected")
```

**State keys per component:**

| Component | State keys |
|-----------|-----------|
| `Tabs` | `active: str` |
| `ViewStack` | `view: str`, `item: dict \| None` |
| `SelectionTable` | `selected_ids: list[int]` |
| `Dialog` | `is_open: bool` |
| `EditCard` | `item_id: int \| None`, `form: dict` |
| `EditDialog` | `item_id: int \| None`, `form: dict`, `dialog: dict` |

### Client Capture Pattern
All UI components inherit `_client` (captured at construction) and `_notify()` method from `RdmComponent`. This ensures `ui.notify()` works safely in async callbacks that may execute after store observers have rebuilt UI elements.

### RDM Component Hierarchy

```
RdmComponent  (_client, _notify, data_source, form/CRUD helpers)
├── DetailCard           (read-only detail view with summary/actions/related layout)
├── EditCard             (in-place editing form, takes FormConfig)
├── EditDialog           (modal editing dialog, takes FormConfig)
└── ObservableRdmComponent  (+ state dict, data list, observe/unobserve/reobserve, load_data, _render_cell)
    └── ObservableRdmTable  (+ TableConfig, filter_by, toolbar, auto_observe, shared load_data)
        ├── ActionButtonTable  (table with action buttons per row)
        ├── ListTable          (read-only clickable rows)
        └── SelectionTable     (checkbox multi-select)

ViewStack                (navigation coordinator — render callbacks for list/detail/edit)
Dialog                   (standalone overlay — context manager, state-driven visibility)
Tabs                     (standalone — binding-driven tab panels)
StepWizard               (standalone — multi-step wizard dialog using Dialog)
```

Components are split by their needs:
- **Detail component** (DetailCard): Extends RdmComponent. Render callbacks for summary + related content. Action buttons (edit/delete). No observer — caller handles refresh.
- **Edit components** (EditCard, EditDialog): Need CRUD helpers but NOT observer. Take `state: dict | None` and `FormConfig`. EditCard renders inline; EditDialog renders in a Dialog overlay. State keys: `item_id`, `form`.
- **Table components** (ActionButtonTable, ListTable, SelectionTable): Inherit from `ObservableRdmTable` which provides shared TableConfig, filter_by, load_data with join field merging, and toolbar rendering. All support `auto_observe` param. SelectionTable exposes `selected_ids` in state.
- **ViewStack**: Navigation shell — manages view switching via `state['view']` and `state['item']`. List panel is pre-rendered with binding-driven visibility (DOM survives navigation); detail/edit panels rebuild on each navigation via `@ui.refreshable_method`.
- **Dialog**: Pure UI positioning, no data source connection. Visibility driven by `state['is_open']` via `bind_visibility_from`. ESC key to close.
- **Tabs**: All panels pre-rendered; `bind_visibility_from(state, "active")` shows the active panel. Only the tab bar (not panels) rebuilds on tab switch.

## Store Module

### EventNotifier (notifier.py)
Manages observer notifications with batching, throttling, and topic filtering:
- **Immediate mode** (`throttle_ms=0`): Events fire immediately
- **Throttled mode** (`throttle_ms>0`): Leading + trailing throttle. The first event flushes immediately; while events keep arriving it flushes at most once per interval; a trailing flush is guaranteed after the last event. Unlike a pure trailing debounce, a sustained sub-interval stream never starves — it flushes on a steady cadence (≤ one flush per interval).
- **Explicit batching**: `async with store.batch()` groups events into single notification (flushes immediately on exit, bypassing the throttle)
- **Topic filtering**: Observers can subscribe with `topics={"field": value}` to receive only matching events
- Coalesces multiple events into `StoreEvent(verb="batch", item={"count": N, "verbs": [...]})`
- Batch events notify ALL observers regardless of topic (conservative approach)

### Store (base.py)
Abstract base class providing CRUD interface with validation, observer notification, derived fields, sorting, and normalization. Uses composition with `EventNotifier` for notification logic. Subclasses implement `_create_item`, `_read_items`, `_update_item`, `_delete_item`, `_read_counts`.

The store is a **CRUD-by-id gateway**, not a cache — it re-reads on every call and writes are keyed by id. Bounding the read/view side is what keeps it scalable (see the bounded-view archetypes below).

Key methods:
- `read_items(filter_by=None, q=None, join_fields=[], limit=None, offset=0, order_by=None)` — bounded reads: `limit`/`offset` page the result and `order_by` sorts DB-side (bypassing the Python `set_sort_key` path). A fully-unbounded read past `unbounded_warn_threshold` (default 1000) rows logs a rate-limited warning.
- `read_counts(filter_by=None, q=None, group_by=None) -> int | dict` — counts without fetching rows: an `int` total, or `dict[value, int]` when `group_by` is set. `MultitenantTortoiseStore` inherits tenant scoping for free (both route through `_build_query`).

- `search_q(text, fields) -> predicate | None` — builds a case-insensitive OR-match over `fields` in the store's own dialect (`TortoiseStore`: an OR of `icontains` `Q`s; `DictStore`: a callable). Returns `None` for empty text or no fields.
- `and_q(a, b)` — composes two predicates so both apply; `None` on either side means "no constraint". This is what keeps a table's own `q` from being clobbered by its search box.

Predicate building lives on the **store**, not the table, so tables stay free of ORM knowledge and search is testable on `DictStore`. Both methods are part of `RdmDataSource`; a custom data source must implement them to use `TableConfig(show_search=True)`. The base `Store` raises `NotImplementedError` from both rather than returning `None` — a store that forgets to implement them fails loudly instead of leaving the search box silently filtering nothing.

**`filter_by` and the observer subscription.** `observe(topics=filter_by)` ties a table's subscription to its scope, so changing `filter_by` must move the subscription too or the table goes deaf to its own new scope. `requery(filter_by=...)` does this for you; a bare `table.filter_by = ...` assignment does not — call `reobserve(topics=...)` after it.

**Derived fields are not queryable — unless you map them.** `set_derived_fields()` computes values *after* the read (`_apply_derived_fields` runs on returned rows), so a derived name is invisible to the database. Passing one to `filter_by`, `order_by` or `group_by` raises a `ValueError` naming the field.

`set_derived_fields(..., query_map={"member_name": ["member__first_name", "member__last_name"]})` gives a derived name real fields to stand in for it: `order_by` uses the **first** mapped field, `search_q` ORs over **all** of them. That is what makes a derived column both sortable and searchable. Without a `query_map`, use `Column.sort_key` to point the header at a real field.

A derived name can also reach the DB *inside* a `q=` predicate, where the up-front check cannot see it. `TortoiseStore` catches the resulting `FieldError` and re-raises a `ValueError` annotated with the store's derived field names; a store with no derived fields keeps the raw `FieldError` (most likely a typo).
- `batch()` — Context manager for explicit notification batching
- `add_observer(callback, topics=None)` — Register observer with optional topic filter
- `remove_observer(callback)` — Unregister observer by callback identity
- `set_topic_fields(fields)` — Configure which fields support topic routing
- `notify_observers()` — Delegates to EventNotifier

#### Bounded-view archetypes
Because a reactive view's re-read cost ≈ its size, every reactive view should be small. Three archetypes:
- **Query-view** — capped/searched table (`limit` + `order_by`, `auto_observe=False`); "N of M" via `read_counts()`.
- **Count-view** — reads counts, not rows, on a throttled cadence, surfaced via NiceGUI binding (`ReactiveCounts`, see Components Module). Bypasses `@ui.refreshable`.
- **Scoped-live-view** — `filter_by` down to a handful of rows; full re-read on throttle is cheap, so `auto_observe=True`.

### DictStore (dict_store.py)
In-memory dict-based Store implementation. Useful for testing and prototyping.

`q` is supported as a **callable predicate** — `q=lambda item: 'ali' in item['name']` — ANDed with `filter_by` and applied before `order_by`/`limit`/`offset`. This lets search and other non-equality filtering be exercised without a database; Tortoise `Q` objects (and any other non-callable) still raise `NotImplementedError`, as do `join_fields`.

`order_by` sorts `None` first ascending and last descending, matching MySQL. **Postgres does the opposite**, so a `DictStore`-backed test can pass while an ORM-backed screen looks wrong on a nullable column. There is no `nulls_last` option; order on a non-nullable field where it matters.

### StoreRegistry (base.py)
Flat `name → Store` registry. Single-tenant apps use this. `store_registry` is the module-level singleton.
`register_store(name, store)` / `get_store(name)` / `get_all_stores() -> list[tuple[name, store]]`

### MultitenantStoreRegistry (multitenancy.py)
Two-level `(tenant, name) → Store` registry for multitenant apps. `mt_store_registry` is the module-level singleton.
`register_store(tenant, name, store)` / `get_store(tenant, name)` / `get_all_stores() -> list[tuple[tenant, name, store]]`

MT apps import it with an alias so call-sites stay readable:
```python
from ng_rdm import mt_store_registry as store_registry
```

### TortoiseStore (orm.py)
ORM-backed Store. Handles:
- Hydration/dehydration for datetime and date fields
- Tortoise Q-object query support
- Join field support for foreign key data (fields with `__` notation)
- DB-side `limit`/`offset`/`order_by` on reads and grouped/total `read_counts`
- `throttle_ms` notification interval (default 100 ms; bump for busy live views)
- `init_db()` helper for database initialization

### MultitenantTortoiseStore (multitenancy.py)
Extends TortoiseStore with automatic tenant scoping on all queries. Validates tenant via `set_valid_tenants()`. Generic bound is `MultitenantRdmModel` — any model passed to this store must subclass `MultitenantRdmModel`. Concrete subclasses must declare their inner Meta as `class Meta(RdmModel.Meta): table = "..."` (inheriting from `RdmModel.Meta`, not `MultitenantRdmModel.Meta`), otherwise `abstract = True` leaks via MRO.

## Components Module

### Package Structure
Infrastructure modules (`base.py`, `protocol.py`, `fields.py`, `i18n.py`, `ng_rdm.css`) live in `components/`. Concrete widget classes live in `components/widgets/` and are re-exported from the top-level `components/__init__.py` so external imports are unchanged.

`fields.py` exports two widget builders:
- `build_form_field(col, state)` — labeled form field for `EditDialog`/`EditCard` (injects `label=`, no `dense flat`)
- `build_cell_field(col, state)` — compact, label-less widget for editable table cells (applies `dense flat`, class `rdm-cell-input`)

### Table Components

| Component | Purpose |
|-----------|---------|
| **ActionButtonTable** | Table with action buttons per row (edit/delete/custom). All actions via callbacks. |
| **ListTable** | Read-only table with clickable rows; accepts `limit`/`order_by` for bounded query-views |
| **SelectionTable** | Table with checkbox column for multi-select |

`ObservableRdmTable` (base of all tables) accepts `limit`/`order_by` and keeps the window (`limit`, `offset`) in its `state` dict, forwarding it to `load_data()` → `read_items()`.

**`q` on tables.** All three widgets accept `q=` and expose it as `self.q`, handled exactly like `filter_by`: assign `table.q` then `await table.build.refresh()` to re-run the query — the supported way to drive a search box, and the reason no table needs subclassing for one. `q` is ANDed with `filter_by` by the store. It takes no part in topic routing, so `observe()` still subscribes on `filter_by` alone; a `q`-filtered live table is refreshed by any event matching its `filter_by` topics.

**State ownership.** A `state` dict passed to a component is *owned* by that component — it may write to it freely. Give each component its own dict (or sub-dict of a page-level `ui_state`); never share one between two components.

### ReactiveCounts (reactive.py)
A throttled, binding-friendly **count-view** for progress/summary headers over large or fast-changing data. Registers a (throttled) store observer and recomputes `read_counts()` into `self.values` — a plain dict, mutated in place — so NiceGUI's `bind_text_from` tracks it without any table rebuild or `@ui.refreshable`. Ungrouped counts land under `key` (default `"total"`); grouped counts use group values as keys (pre-seed via `keys=` so bindings always resolve). Captures `ui.context.client` at `start()` and unobserves on `client.on_disconnect`.
```python
counts = ReactiveCounts(store, group_by="status", keys=["delivered", "pending"])
await counts.start()
ui.label().bind_text_from(counts.values, "delivered", backward=lambda v: str(v or 0))
```

### ActionButtonTable Configuration

ActionButtonTable displays data with per-row action buttons. All action semantics are delegated to client callbacks. The add button is rendered in the table toolbar when `config.show_add_button` is True **and** an `on_add` callback is set — `add_button` is only the label, so it cannot imply a handler. Toolbars are rendered by `render()`, not `build()`.

```python
ActionButtonTable(
    data_source,                 # RdmDataSource
    config,                      # TableConfig (with custom_actions as RowAction list)
    state=None,                  # Optional state dict
    filter_by=None,              # Filter data loading
    on_add=None,                 # Callback when Add clicked
    on_edit=None,                # Callback when Edit clicked (receives row dict)
    on_delete=None,              # Callback when Delete clicked (receives row dict)
    render_toolbar=None,         # Custom toolbar render callback
    auto_observe=True,           # Auto-subscribe to data source
)
```

### EditDialog

Modal dialog for creating/editing items. Wraps form fields in a Dialog overlay.

```python
dlg = EditDialog(state=ui_state["edit"], data_source=store, config=form_config, on_saved=handle_saved)
dlg.open_for_new()           # Open for creating new item
dlg.open_for_edit(item)      # Open for editing existing item
```

Typical wiring with ActionButtonTable:
```python
dlg = EditDialog(state=ui_state["edit"], data_source=store, config=form_config,
                 on_saved=lambda _: table.build.refresh())
table = ActionButtonTable(
    state=ui_state["table"], data_source=store, config=table_config,
    on_add=dlg.open_for_new,
    on_edit=dlg.open_for_edit,
)
```

### Supporting Components
- **Dialog** — Positioned card overlay (alternative to ui.dialog). Context manager with `actions()` slot.
- **DetailCard** — Read-only detail view with `render_summary` and `render_related` callbacks. Edit/Delete action buttons.
- **EditCard** — In-place editing form using FormConfig (for ViewStack edit view)
- **EditDialog** — Modal editing dialog using FormConfig (for table-triggered editing)
- **ViewStack** — Navigation coordinator with render callbacks: `render_list(vs)`, `render_detail(vs, item)`, `render_edit(vs, item|None)`. Back-arrow navigation.
- **Tabs** — Tab switcher for multiple views
- **StepWizard** — Multi-step form wizard using Dialog, with WizardStep definitions
- **Button, IconButton, Icon** — RDM-styled button/icon primitives using Bootstrap Icons
- **Row, Col, Separator** — Lightweight layout primitives (flexbox wrappers)

### RowAction
`RowAction` dataclass configures per-row action buttons:
- `icon` — Bootstrap icon name (renders as icon if set)
- `label` — Button text (used when no icon)
- `tooltip`, `color` ("primary", "secondary", "danger")
- `callback` — Async or sync function called with row dict

### How the config pieces fit together

`Column` is the shared unit between tables and forms. A single list of `Column` objects is passed to both `TableConfig` (which uses it to render table rows) and `FormConfig` (which uses it to render form fields) — so field metadata is declared once. At construction time:

- `TableConfig.__post_init__` derives `join_fields` from column names containing `__`, so FK data is fetched automatically.
- `FormConfig.__post_init__` sets `focus_column` to the first column if not explicitly given.
- Both configs copy `width_style` from `width_percent` into a CSS flex value.

**Rendering escape hatches** — the config handles the common case; for anything else, columns carry callbacks that take over for that one concern without disrupting the rest of the config:

| Hook | Where used | What it does |
|---|---|---|
| `Column.formatter(value) → str` | table cells | format the display string (e.g. date, currency) |
| `Column.render(row) → None` | table cells | emit custom HTML for the whole cell (e.g. chips) |
| `Column.on_click(row) → None` | table cells | make a cell value a clickable link |
| `TableConfig.custom_actions` | per-row action column | extra `RowAction` buttons beyond edit/delete |
| `ObservableRdmTable.render_toolbar` | toolbar slot | inject custom controls (filters, exports, etc.) |

`Column.render` and `Column.formatter` are mutually exclusive: if `render` is set, the whole cell is delegated; otherwise `formatter` is applied to the value before display.

### Column Configuration
`Column` dataclass configures table columns and form fields:
- `name`, `label`, `width_percent` (column width as percentage)
- `ui_type`: input, number, select, checkbox, badge, textarea, label, html, markdown
- `default_value`, `parms` (passed to ui_type constructor), `props` (passed to el.props())
- `formatter`, `render` (custom rendering callable)
- `on_click` (per-column click handler)
- `required`, `editable`, `placeholder`
- `sortable`, `sort_key`, `sort_desc_first` — opt a column into header-click sorting (see below)
- Fields with `__` in the name auto-derive join_fields for FK data

**Header-click sorting** — set `Column.sortable=True` to make a header clickable; each click toggles ascending↔descending on `sort_key or name`. The table drives its own `order_by` (a per-instance attribute) and delegates the sort to `read_items(order_by=...)` — so it is DB-side for `TortoiseStore`, correct under `limit`/`offset` paging (order is applied before the window; a row-key tie-break keeps pages stable), and independent per subscriber (tables sharing a store sort separately; the shared `Store.set_sort_key` is never used). Only mark columns backed by a real queryable field — a derived name raises (see Store).

`sort_desc_first=True` opens the column descending on the *first* click, for dates and counts where newest/largest first is what the user wants; toggling is unchanged.

**Sorting moves the window.** `_toggle_sort` resets `state["offset"] = 0` before refreshing, so the table returns to page one. Any paging chrome rendered *outside* the table must therefore read `table.state` (or bind to it) rather than mirror the offset in its own variable — otherwise the counter and prev/next go stale on a header click.

**Selection survives a re-sort — and a page change.** `SelectionTable` keys `state['selected_ids']` on `row_key`, not on row position, so re-sorting or paging leaves the selection intact.

> ⚠️ **A bulk action can therefore operate on rows the user cannot see.** Select on page 1, page to page 2, hit "delete selected" — page 1's rows go too. This is deliberate (cross-page selection is legitimate), so it is surfaced rather than silently changed: every read publishes `selected_count` and `selected_offscreen` into `state`, and the built-in pager label appends "N selected (M off page)". Pass `SelectionTable(clear_selection_on_page_change=True)` for page-scoped selection instead. If you render your own bulk-action bar, bind it to those keys.

### The toolbar is rendered once, outside the refreshable

`build()` is `@ui.refreshable_method` — everything inside it is destroyed and rebuilt on every store event and every sort click. That is fine for rows, fatal for a search input, which would lose focus and value on the refresh its own keystroke triggered.

So `render()` is the entry point: it renders the toolbar slots **once**, around `build()`. Toolbar content that depends on data does not re-render — it **binds** to `self.state`, the same pattern `ReactiveCounts` uses. Every read publishes the window's numbers there:

| key | meaning |
|---|---|
| `total` | matching rows (`None` when nothing displays a total — see below) |
| `shown` | rows on this page |
| `page_first`, `page_last` | 1-based row numbers of the current window (`0` when empty) |
| `has_prev`, `has_next` | whether a previous/next page exists |
| `page_label` | formatted label — `pager_label(first, last, total)` if given |
| `selected_count`, `selected_offscreen` | `SelectionTable` only |

The raw keys are the point: an app can bind its own counter with its own wording (`ui.label().bind_text_from(table.state, "page_label")`, `Button(...).bind_enabled_from(table.state, "has_next")`) instead of taking the built-in chrome. Because `_toggle_sort` resets `state["offset"]`, bound chrome stays correct on a header click for free.

**Counting costs a query, so it is skipped unless something shows it.** A first page that came back under its own `limit` is already the whole result set (free). Otherwise a `COUNT` runs only when `show_pager` is set or a `pager_label` is supplied — without that, `total` is `None` and `has_next` falls back to "this page is full". This matters on an `auto_observe=True` table, where a COUNT per read means a COUNT per store event.

### TableConfig
`TableConfig` dataclass configures table display:
- `columns` — Columns displayed in table view
- `show_edit_button`, `show_delete_button`, `show_add_button` — the add button also needs an `on_add` handler; `add_button` is only its label, so it cannot imply one
- `add_button` — Custom text for add button
- `custom_actions` — List of `RowAction` for custom per-row buttons
- `empty_message` — Message when table is empty (rendered as a row *inside* the table, so headers and the sort affordance survive)
- `toolbar_position` — slot for the add button and `render_toolbar` ("top"/"bottom", default "bottom")
- `search_position` (default "top"), `pager_position` (default "bottom") — each toolbar element carries its own slot, so search-top / pager-bottom is expressible. Assigning both to the same slot puts them in one toolbar row (search left, pager right-aligned)
- `show_pager` — label + prev/next, bound to the published state. Needs `limit` on the table
- `pager_label` — `(first, last, total) -> str`; supplying one also switches counting on, for apps that render their own chrome
- `show_search`, `search_fields` — debounced search box; the predicate comes from the store's `search_q()` and is ANDed with the table's own `q` via `and_q()`
- `search_placeholder`, `search_debounce` (ms, default 300)

> **`show_search` wants `auto_observe=False`.** `q` takes no part in topic routing, so a searched *and* observed table re-reads on every store event regardless of relevance — exactly the cost bounded views exist to avoid.

### FormConfig
`FormConfig` dataclass configures form/dialog behavior:
- `columns` — Columns rendered as form fields
- `title_add`, `title_edit` — Dialog titles
- `dialog_class` — CSS class for dialog styling
- `focus_column` — Default column for focus
- `delete_confirmation` — Whether to confirm deletes

### Localization (i18n.py)
Built-in Dutch/English translations for UI strings. Configurable via `set_language()` and `set_translations()`.

## Models Module

### FieldSpec & Validator (types.py)
- `Validator(message, validator_fn)` — Named tuple for field validation
- `FieldSpec(validators, normalizer)` — Named tuple for field configuration

### RdmModel (rdm_model.py)
Extends Tortoise ORM Model with:
- Auto-generated required-field validators for non-nullable text fields
- `get_all_field_specs()` classmethod merging explicit + auto specs
- `get_field_names()` / `get_join_field_types()` for introspection
- `values()` instance method for dict conversion with field selection

### MultitenantRdmModel (mt_rdm_model.py)
Abstract subclass of `RdmModel` for use with `MultitenantTortoiseStore`. Declares `tenant = fields.CharField(max_length=64, index=True)` once, consistently, and indexed. Models that go into tenant-scoped stores subclass this instead of `RdmModel`. Concrete subclasses must declare `class Meta(RdmModel.Meta): table = "..."` — NOT `MultitenantRdmModel.Meta` — to avoid inheriting `abstract = True` via MRO.

## Utils Module

### helpers.py
- Date/time conversion: `local_to_utc()`, `utc_to_local()`, hydration/dehydration helpers
- Default timezone: `Europe/Amsterdam` (configurable via `TIMEZONE_STRING`)
- Validation: `vali_date_str()`, `valid_time_string()`, `equal_dicts()`
- String utilities: `generate_random_string()`, `str_remove_chars()`
- UI helpers: `div()`, `div_full()`, `Config` (dict with dot notation)

### logging.py
`setup_logging()` — configurable file/console logging with separate levels for tortoise, uvicorn, and optional SQL query logging.

## Debug Module

Real-time event stream visualization for development and troubleshooting.

### EventLog (event_log.py)
Global singleton (`event_log`) providing:
- Rotating buffer of store events (default 200 entries)
- `EventLogEntry` dataclass with timestamp, store name, tenant, observer, topics, event, notified flag
- `StoreStats` for per-store statistics (observer count, event count, last event time)
- Listener support for live UI updates

### Debug Page (page.py)
`enable_debug_page(path="/rdm-debug")` registers a NiceGUI page showing:
- Store overview table (all registered stores, observer counts, event counts)
- Live event stream with verb-colored badges (create=green, update=blue, delete=red, batch=gray)
- Topic filtering visibility (shows when observers were filtered out)

Usage:
```python
from ng_rdm.debug import enable_debug_page
enable_debug_page()  # Then visit /rdm-debug
```

Demo: `python -m ng_rdm.examples.catalog` (includes debug page)

## Technologies

- **Python 3.12+**
- **NiceGUI** — Python web UI framework
- **Tortoise ORM** — async ORM
- **pytz** — timezone handling
- **Build**: hatchling
- **Testing**: pytest + pytest-asyncio

## Technical debt / to revisit

- table.build vs table.build_with_toolbar - table.build should include the latter?
- detail_card.on_delete and .on_deleted - are the complicated semantics justified?
- IconButton with label, currently icon-only for no reason
- add Card that doesn't produce the usual Quasar junk