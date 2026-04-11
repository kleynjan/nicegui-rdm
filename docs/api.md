# ng_rdm API Reference

Full API reference for ng_rdm. For architecture, design patterns, and the observer model, see [facts.md](facts.md).

---

## Quick import reference

```python
# Store layer
from ng_rdm import (
    Store, DictStore, TortoiseStore, MultitenantTortoiseStore,
    StoreRegistry, store_registry,
    MultitenantStoreRegistry, mt_store_registry,
    StoreEvent, TenancyError,
    init_db, set_valid_tenants,
)

# Model helpers
from ng_rdm.models import RdmModel, MultitenantRdmModel, FieldSpec, Validator
# or: from ng_rdm import RdmModel, MultitenantRdmModel, FieldSpec, Validator

# Components
from ng_rdm.components import (
    rdm_init, Column, TableConfig, FormConfig, RowAction, RdmDataSource,
    ActionButtonTable, ListTable, SelectionTable,
    EditDialog, EditCard, DetailCard, Dialog,
    ViewStack, Tabs, StepWizard, WizardStep,
    Button, IconButton, Icon, Row, Col, Separator,
    confirm_dialog, set_language, set_translations, none_as_text,
)

# Utilities
from ng_rdm import configure_logging, logger

# Debug
from ng_rdm import enable_debug_page
```

---

## Store Layer

### `Store` (abstract base — `store/base.py`)

Abstract base class. Do not instantiate directly; use `DictStore` or `TortoiseStore`.

**CRUD — overridden by subclasses:**

```python
await store.create_item(item: dict) -> dict | None
await store.read_items(filter_by=None, q=None, join_fields=[]) -> list[dict]
await store.read_item_by_id(id: int, join_fields=[]) -> dict | None
await store.update_item(id: int, partial_item: dict) -> dict | None
await store.delete_item(item: dict) -> None
```

**Observer management:**

```python
store.add_observer(callback, topics=None)   # register observer, optional topic filter
store.remove_observer(callback)             # unregister by callback identity
store.set_topic_fields(fields: list[str])   # declare fields eligible for topic routing
store.observer_count                        # property: number of registered observers
```

**Validation:**

```python
store.validate(item: dict) -> tuple[bool, dict]   # (valid, errors_by_field)
store.field_specs                                  # property: merged FieldSpec dict
```

**Batching:**

```python
async with store.batch():
    await store.create_item(item1)
    await store.create_item(item2)
# Single batch StoreEvent fires here
```

**Sorting and derived fields:**

```python
store.set_sort_key(key_func, reverse=False)
store.set_derived_fields(derived_fields: dict[str, Callable], dependencies=None)
```

### `DictStore` (`store/dict_store.py`)

In-memory dict-based store. Same CRUD API as `TortoiseStore`. Useful for prototyping, non-persistent data, and testing.

```python
store = DictStore()
```

### `TortoiseStore` (`store/orm.py`)

ORM-backed store using Tortoise ORM. Generic: `TortoiseStore[T]` where `T` is a `RdmModel` subclass.

```python
store = TortoiseStore(ModelClass, debounce_ms=100)
```

- Default `debounce_ms=100`: rapid mutations are coalesced into a single notification after 100ms quiet.
- Handles hydration/dehydration for `DatetimeField` and `DateField`.
- Supports `join_fields` for FK navigation (e.g. `"category__name"` → joins related model).
- Supports Tortoise Q-objects via the `q=` parameter on `read_items`.

**Subclassing (common pattern):**

```python
class EnrichedProductStore(TortoiseStore[Product]):
    async def _read_items(self, filter_by=None, q=None, join_fields=[]):
        items = await super()._read_items(filter_by, q, join_fields)
        # add computed fields, enrich with related data, etc.
        return items
```

### `MultitenantTortoiseStore` (`store/multitenancy.py`)

Extends `TortoiseStore` with automatic tenant scoping on all queries. Model must subclass `MultitenantRdmModel`.

```python
store = MultitenantTortoiseStore(ModelClass, tenant="acme")
```

All CRUD operations automatically filter/set the `tenant` field. Raises `TenancyError` for unknown tenants.

### `StoreRegistry` / `store_registry` (`store/base.py`)

Flat `name → Store` registry for single-tenant apps. `store_registry` is the module-level singleton.

```python
store_registry.register_store("product", TortoiseStore(Product))
store = store_registry.get_store("product")
stores = store_registry.get_all_stores()   # list[tuple[name, store]]
```

### `MultitenantStoreRegistry` / `mt_store_registry` (`store/multitenancy.py`)

Two-level `(tenant, name) → Store` registry for multitenant apps. `mt_store_registry` is the module-level singleton.

```python
mt_store_registry.register_store(tenant, "product", MultitenantTortoiseStore(Product, tenant=tenant))
store = mt_store_registry.get_store(tenant, "product")
stores = mt_store_registry.get_all_stores()   # list[tuple[tenant, name, store]]
```

MT apps typically alias to keep call-sites readable:

```python
from ng_rdm import mt_store_registry as store_registry
```

### `StoreEvent`

Named tuple emitted to observers.

```python
@dataclass
StoreEvent:
    verb: str      # "create", "update", "delete", "batch"
    item: dict     # the affected item; for "batch": {"count": N, "verbs": [...]}
```

### `init_db`

Initializes Tortoise ORM with a NiceGUI/FastAPI app.

```python
init_db(
    app,                                    # NiceGUI app (wraps FastAPI)
    db_url: str,                            # e.g. "sqlite://app.db", "postgres://..."
    modules: dict[str, list[str]],          # e.g. {"models": ["myapp.models"]}
    generate_schemas: bool = False,         # auto-create tables (dev only)
)
```

Teardown is handled automatically via FastAPI's lifespan protocol.

### `set_valid_tenants`

Declares the allowed tenant identifiers for `MultitenantTortoiseStore`.

```python
from ng_rdm import set_valid_tenants
set_valid_tenants(["acme", "brutus"])
```

---

## Models

### `RdmModel` (`models/rdm_model.py`)

Extends Tortoise ORM `Model`. Base class for all ng_rdm models.

```python
class Product(RdmModel):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)

    field_specs = {
        "name": FieldSpec(validators=[
            Validator(message="Name is required", validator=lambda v, _: bool(v and v.strip()))
        ])
    }

    class Meta(RdmModel.Meta):
        table = "product"
```

**Notes:**
- Every table must have an integer primary key called `id`.
- `field_specs` is a class attribute: `dict[str, FieldSpec]`.
- Auto-generates required-field validators for non-nullable `CharField`/`TextField` fields not in `field_specs`.

**Class methods:**

```python
Product.get_all_field_specs()       # merged explicit + auto-generated FieldSpec dict
Product.get_field_names(join_fields=[])
Product.get_join_field_types()      # dict of FK join field names → ORM field type
Product.get_field_types()           # list[dict] of field metadata
```

### `MultitenantRdmModel` (`models/mt_rdm_model.py`)

Abstract subclass of `RdmModel` for multitenant stores. Adds `tenant = CharField(max_length=64, index=True)` automatically.

```python
class Product(MultitenantRdmModel):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    # `tenant` inherited — do not declare it

    class Meta(RdmModel.Meta):      # inherit from RdmModel.Meta, NOT MultitenantRdmModel.Meta
        table = "products"          # (avoids inheriting abstract=True via MRO)
```

### `FieldSpec` and `Validator` (`models/types.py`)

```python
Validator(
    message: str,                   # error message shown in UI
    validator: Callable[[value, item_dict], bool],
)

FieldSpec(
    validators: list[Validator] = [],
    normalizer: Callable[[value], value] | None = None,   # called before save
)
```

The validator receives the field value and the full item dict (for cross-field validation).

---

## Page Initialization

### `rdm_init()`

Must be called once per page render, at the top of each `@ui.page` function.

```python
rdm_init(
    custom_translations=None,         # dict[str, dict[str, str]] — extend/override i18n
    extra_css=None,                   # str — additional CSS string or file path
    show_refresh_transitions=False,   # animated green border on component rebuilds
    show_store_event_log=False,       # enable /rdm-debug event stream page
)
```

---

## Configuration Dataclasses

### `Column`

Configures a table column or form field.

```python
Column(
    name: str,                        # field name (matches data dict key)
    label: str | None = None,         # display label (defaults to name)
    ui_type: Any = None,              # ui.input, ui.number, ui.select, ui.checkbox,
                                      # ui.textarea, ui.badge, ui.label, ui.html, ui.markdown
    default_value: Any = "",          # default for new items
    parms: dict = {},                 # kwargs passed to ui_type constructor
    props: str = "",                  # passed to el.props() (Quasar props string)
    width_percent: float | None,      # column width as percentage (0-100)
    placeholder: str | None = None,
    required: bool = False,           # validation: field cannot be empty
    editable: bool = True,            # if False, displayed as label in edit mode
    on_click: Callable[[dict], ...],  # per-column click handler (receives row dict)
    formatter: Callable[[Any], str],  # display formatter for table cells
    render: Callable[[dict], None],   # custom render (receives row dict, replaces cell)
)
```

- Fields with `__` in the name (e.g. `"category__name"`) auto-derive join fields for FK data.
- `ui_type` of `ui.badge`, `ui.label`, `ui.html`, `ui.markdown` are display-only (skipped in forms).
- For `ui.badge`: use `parms={"color_map": {"value": "color"}}` for value-based coloring (ListTable only).

### `TableConfig`

```python
TableConfig(
    columns: list[Column] = [],
    empty_message: str | None = None,      # shown when table has no data
    add_button: str | None = None,         # custom Add button text
    show_add_button: bool = True,
    show_edit_button: bool = True,         # ActionButtonTable only
    show_delete_button: bool = True,       # ActionButtonTable only
    custom_actions: list[RowAction] = [],  # additional per-row action buttons
    toolbar_position: "top" | "bottom" = "bottom",
)
```

### `FormConfig`

```python
FormConfig(
    columns: list[Column] = [],
    title_add: str | None = None,          # dialog title for new items
    title_edit: str | None = None,         # dialog title for editing
    dialog_class: str | None = None,       # CSS class for dialog sizing
    focus_column: str | None = None,       # auto-focused column (defaults to first)
    delete_confirmation: bool = True,
)
```

### `RowAction`

Configures a per-row action button in ActionButtonTable.

```python
RowAction(
    icon: str | None = None,               # Bootstrap icon name (e.g. "send", "eye")
    label: str | None = None,              # button text (used when no icon)
    tooltip: str = "",
    callback: Callable[[dict], ...],       # called with row dict
    color: str = "primary",                # "primary", "secondary", "danger", "default"
)
```

---

## Table Components

All table components extend `ObservableRdmTable` and share:
- Auto-observe data source (configurable via `auto_observe`)
- `build()` renders the table (call with `await`)
- `build_with_toolbars()` wraps `build()` with toolbar at configured position
- `filter_by` dict for scoping data queries
- `transform` callback for post-load data transformation
- `render_toolbar` callback for custom toolbar content

**Custom table subclasses** — subclass `ObservableRdmTable` to build bespoke table behaviour (e.g. inline per-cell editing). Implement `@ui.refreshable_method async def build(self)`, call `self.load_data()` and `self._build_toolbar("top"/"bottom")`, and use `self._render_cell(col, value, row)` for read-only cells. For editable cells, use `build_cell_field(col, row_dict)` from `ng_rdm.components.fields`. See `examples/in_row_editing.py` for a full working example.

### `ActionButtonTable`

Table with per-row action buttons (edit, delete, custom).

```python
table = ActionButtonTable(
    data_source,                           # RdmDataSource
    config,                                # TableConfig
    state=None,                            # dict | None
    *,
    filter_by=None,                        # dict — filter data loading
    on_add=None,                           # Callable — Add button clicked
    on_edit=None,                          # Callable[[dict], ...] — Edit clicked
    on_delete=None,                        # Callable[[dict], ...] — Delete clicked
    render_toolbar=None,                   # Callable — custom toolbar content
    auto_observe=True,
)
await table.build()
```

Edit/delete buttons are auto-generated from `config.show_edit_button`/`show_delete_button`. Custom actions come from `config.custom_actions`.

**Typical wiring with EditDialog:**

```python
dlg = EditDialog(data_source=store, config=form_config)
table = ActionButtonTable(
    data_source=store, config=table_config,
    on_add=dlg.open_for_new,
    on_edit=dlg.open_for_edit,
)
```

### `ListTable`

Read-only table with clickable rows.

```python
table = ListTable(
    data_source,
    config,                                # TableConfig
    filter_by=None,
    on_click=None,                         # Callable[[int | None], ...] — receives row key
    on_add=None,
    transform=None,                        # Callable[[list[dict]], list[dict]]
    row_key="id",
    join_fields=None,
    render_toolbar=None,
    auto_observe=True,
)
await table.build()
```

Supports `ui.badge` rendering via `Column(ui_type=ui.badge, parms={"color_map": {...}})`.

### `SelectionTable`

Table with checkbox column for multi-select.

```python
table = SelectionTable(
    data_source,
    config,                                # TableConfig
    state=None,
    show_checkboxes=True,
    multi_select=True,
    *,
    filter_by=None,
    transform=None,
    row_key="id",
    join_fields=None,
    on_selection_change=None,              # Callable[[set[int]], None]
    render_toolbar=None,
    auto_observe=True,
)
await table.build()
```

**Selection methods:**
- `table.selected_ids` — property returning `list[int]`
- `table.toggle(row_key)`, `table.select_all()`, `table.clear_selection()`
- `table.add_to_selection(row_key)`, `table.remove_from_selection(row_key)`

**State keys:** `selected_ids: list[int]`, `show_checkboxes: bool`, `multi_select: bool`

---

## Form Components

### `EditDialog`

Modal dialog for creating/editing items.

```python
dlg = EditDialog(
    data_source,                           # RdmDataSource
    config,                                # FormConfig
    state=None,                            # dict | None — keys: item_id, form, dialog
    *,
    on_saved=None,                         # Callable[[dict], None] — receives saved item
)
dlg.open_for_new()                         # open for creating new item
dlg.open_for_edit(item)                    # open for editing existing item
```

**State keys:** `item_id: int | None`, `form: dict`, `dialog: dict`

### `EditCard`

In-place editing form (typically inside ViewStack's edit view).

```python
card = EditCard(
    data_source,                           # RdmDataSource
    config,                                # FormConfig
    state=None,                            # dict | None — keys: item_id, form
    *,
    on_saved=None,                         # Callable[[dict], None]
    on_cancel=None,                        # Callable[[], None]
)
card.set_item(item)                        # load item for editing, or None for new
await card.build()
```

**State keys:** `item_id: int | None`, `form: dict`

---

## Display Components

### `DetailCard`

Read-only detail view with summary, action buttons, and optional related content.

```python
detail = DetailCard(
    data_source,                           # RdmDataSource (used for delete)
    render_summary,                        # async Callable[[dict], None]
    state=None,                            # dict | None — key: item
    *,
    render_related=None,                   # async Callable[[dict], None]
    on_edit=None,                          # Callable[[dict], None]
    on_deleted=None,                       # Callable[[], None]
    show_edit=True,
    show_delete=True,
)
detail.set_item(item)
await detail.build()
```

No observer integration — the caller (ViewStack or page-level) handles refresh.

### `Dialog`

Positioned card overlay. Context manager for building dialog content.

```python
with Dialog(
    state=None,                            # dict | None — key: is_open
    title=None,                            # str
    dialog_class="",                       # additional CSS class
    on_close=None,                         # Callable
) as dlg:
    ui.input("Name")
    with dlg.actions():
        Button("Save", on_click=handle_save)
        Button("Cancel", color="secondary", on_click=dlg.close)
```

**Methods:** `dlg.open()`, `dlg.close()`, `dlg.actions()` (footer context manager)

**State keys:** `is_open: bool`, `title: str` (if title provided)

ESC key closes the dialog.

---

## Navigation Components

### `ViewStack`

Coordinates list/detail/edit views with back-arrow navigation.

```python
vs = ViewStack(
    render_list,                           # async Callable[[ViewStack], None]
    render_detail,                         # async Callable[[ViewStack, dict], None]
    render_edit,                           # async Callable[[ViewStack, dict | None], None]
    state=None,                            # dict | None — keys: view, item
)
await vs.build()
```

**Navigation methods:** `vs.show_list()`, `vs.show_detail(item)`, `vs.show_edit_existing(item)`, `vs.show_edit_new()`, `vs.go_back()`

**State keys:** `view: str` ("list", "detail", "edit"), `item: dict | None`

The list panel is rendered once with binding-driven visibility — the list component's store observer stays alive while navigating to detail/edit.

### `Tabs`

Tab bar with pre-rendered panels.

```python
tabs = Tabs(
    tabs=[
        ("guests", "Guests", render_guests),   # (key, label, async render callback)
        ("admins", "Admins", render_admins),
    ],
    state=None,                            # dict | None — key: active
)
await tabs.build()
```

**State keys:** `active: str` (defaults to first tab's key)

---

## Wizard

### `StepWizard` and `WizardStep`

```python
WizardStep(
    name: str,
    title: str,
    render: Callable[[dict], Awaitable],   # async, receives wizard state dict
    validate: Callable[[dict], bool] | None,
    next_label: str = "Next ->",
    back_label: str = "<- Back",
)

wizard = StepWizard(
    steps=[WizardStep(...)],
    on_complete,                           # async Callable[[dict], None] — receives final state
    cancel_label="Cancel",
    complete_label="Create",
)
await wizard.show()
```

---

## Buttons & Layout

```python
Button(text="", on_click=None, color="primary")          # "primary", "secondary", "danger", etc.
IconButton(icon="pencil", on_click=None, color="primary", tooltip="Edit")
Icon(icon="check", on_click=None, color="primary", tooltip="Done")

with Row(gap="1rem", align="center", classes="", style=""): ...
with Col(gap="1rem", classes="", style=""): ...
Separator(classes="", style="")
```

Icon names are Bootstrap Icons identifiers (e.g. `"pencil"`, `"trash"`, `"eye"`, `"send"`).

---

## Utilities

### `configure_logging` / `logger`

```python
from ng_rdm import configure_logging, logger

# Call once before startup:
configure_logging(log_file="app.log", console=True)

# Use in app code:
logger.info("My message")
```

Routes ng_rdm, Tortoise ORM, and uvicorn output to file/console. Without calling it, ng_rdm stays silent and defers to the host app's logging config.

### `build_cell_field` / `build_form_field`

From `ng_rdm.components.fields` (not re-exported from top-level):

```python
from ng_rdm.components.fields import build_cell_field, build_form_field

# Compact label-less widget for editable table cells:
el = build_cell_field(col, row_dict)    # returns None for display-only types
if el:
    el.on("blur", lambda _: handle_save())

# Labeled form field for dialogs/cards:
el = build_form_field(col, state_dict)  # used internally by EditDialog, EditCard
```

### `confirm_dialog`

```python
from ng_rdm.components import confirm_dialog

confirmed = await confirm_dialog(
    item=None,          # dict — for {field_name} format string substitution
    prompts=None,       # dict: question, explanation, yes_button, no_button
)
```

### Localization

```python
from ng_rdm.components import set_language, set_translations

set_language("nl_nl")                                   # built-in: "en_gb" (default), "nl_nl"
set_translations({"nl_nl": {"Save": "Opslaan"}})        # extend/override
```

---

## Debug

### `enable_debug_page`

```python
from ng_rdm import enable_debug_page
enable_debug_page(path="/rdm-debug")    # registers the debug route
```

Or pass `show_store_event_log=True` to `rdm_init()`. Then visit `/rdm-debug` for:
- Store overview: all registered stores, observer counts, event counts
- Live event stream with verb-colored badges

---

## Observer Lifecycle

Components using `ObservableRdmComponent` (or `ObservableRdmTable`) support:

```python
component.observe(topics=None)       # start observing, with optional topic filter
component.unobserve()                # stop observing
component.reobserve(topics=None)     # update topic subscription
```

`ObservableRdmTable` auto-observes when `auto_observe=True` (default). Auto-cleanup: when a component's DOM context is gone, `_handle_datasource_change` auto-unobserves via `build.prune()`.

### Topic filtering

```python
store.set_topic_fields(["tenant_id", "country"])        # declare eligible fields
store.add_observer(callback, topics={"country": "UK"})  # observer only notified for UK events
```

Multiple keys are AND-ed. When events are coalesced (debounce or `batch()`), topic matching is bypassed and all observers are notified conservatively.
