# Components API Reference

API reference for ng_rdm UI components. For architecture and design patterns, see `facts.md`.

All components are imported from `ng_rdm.components`:

```python
from ng_rdm.components import (
    rdm_init, Column, TableConfig, FormConfig, RowAction, RdmDataSource,
    ActionButtonTable, ListTable, SelectionTable,
    EditDialog, EditCard, DetailCard, Dialog,
    ViewStack, Tabs, StepWizard, WizardStep,
    Button, IconButton, Icon, Row, Col, Separator,
    confirm_dialog, set_language, set_translations, none_as_text,
)
```

---

## Page Initialization

### `rdm_init()`

Must be called once per page render. Loads Bootstrap Icons CDN and `ng_rdm.css`.

```python
rdm_init(
    custom_translations=None,         # dict[str, dict[str, str]] — extend/override i18n
    extra_css=None,                   # str — additional CSS string or file path
    show_refresh_transitions=False,   # highlight refreshable components on update
    show_store_event_log=False,       # enable /rdm-debug page
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
    render: Callable[[dict], None],   # custom render function (receives row dict, replaces default cell)
)
```

- Fields with `__` in the name (e.g. `"category__name"`) auto-derive join fields for FK data.
- `ui_type` of `ui.badge`, `ui.label`, `ui.html`, `ui.markdown` are display-only (skipped in forms).
- For `ui.badge`: use `parms={"color_map": {"value": "color"}}` for value-based coloring (ListTable only).

### `TableConfig`

Configures table display components.

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

Configures form/dialog components.

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

All table components extend `ObservableRdmTable` and share these features:
- Auto-observe data source (configurable via `auto_observe`)
- `build()` renders the table (call with `await`)
- `build_with_toolbars()` wraps `build()` with toolbar at configured position
- `filter_by` dict for scoping data queries
- `transform` callback for post-load data transformation
- `render_toolbar` callback for custom toolbar content

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

Edit/delete buttons are auto-generated from `config.show_edit_button`/`show_delete_button`. Custom actions come from `config.custom_actions`. All render as `RowAction` icons.

**Typical wiring with EditDialog:**

```python
dlg = EditDialog(data_source=store, config=form_config,
                 on_saved=lambda _: table.build.refresh())
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
    on_click=None,                         # Callable[[int | None], ...] — row clicked, receives row key
    on_add=None,
    transform=None,                        # Callable[[list[dict]], list[dict]]
    row_key="id",                          # field used as row identifier
    join_fields=None,                      # list[str] — additional join fields
    render_toolbar=None,
    auto_observe=True,
)
await table.build()
```

- Supports `ui.badge` rendering via `Column(ui_type=ui.badge, parms={"color_map": {...}})`.

### `SelectionTable`

Table with checkbox column for multi-select.

```python
table = SelectionTable(
    data_source,
    config,                                # TableConfig
    state=None,
    show_checkboxes=True,                  # show/hide checkbox column
    multi_select=True,                     # allow multiple selections
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
- `table.selected_ids` — property returning `list[int]` of selected IDs
- `table.toggle(row_key)` — toggle selection for a row
- `table.select_all()` / `table.clear_selection()`
- `table.add_to_selection(row_key)` / `table.remove_from_selection(row_key)`

**State keys:** `selected_ids: list[int]`, `show_checkboxes: bool`, `multi_select: bool`

---

## Form Components

### `EditDialog`

Modal dialog for creating/editing items. Wraps form fields in a Dialog overlay.

```python
dlg = EditDialog(
    data_source,                           # RdmDataSource
    config,                                # FormConfig
    state=None,                            # dict | None — keys: item_id, form, dialog
    *,
    on_saved=None,                         # Callable[[dict], None] — receives saved item
)
```

**Methods:**
- `dlg.open_for_new()` — open dialog for creating new item
- `dlg.open_for_edit(item)` — open dialog for editing existing item
- `dlg.is_new` — property, True if creating new item

**State keys:** `item_id: int | None`, `form: dict`, `dialog: dict`

### `EditCard`

In-place editing form (typically used inside ViewStack's edit view).

```python
card = EditCard(
    data_source,                           # RdmDataSource
    config,                                # FormConfig
    state=None,                            # dict | None — keys: item_id, form
    *,
    on_saved=None,                         # Callable[[dict], None]
    on_cancel=None,                        # Callable[[], None]
)
```

**Methods:**
- `card.set_item(item)` — load item for editing, or `None` for new-item mode
- `await card.build()` — render the form
- `card.is_new` — property

**State keys:** `item_id: int | None`, `form: dict`

---

## Display Components

### `DetailCard`

Read-only detail view with summary, action buttons, and optional related content.

```python
detail = DetailCard(
    data_source,                           # RdmDataSource (used for delete)
    render_summary,                        # async Callable[[dict], None] — render item attributes
    state=None,                            # dict | None — key: item
    *,
    render_related=None,                   # async Callable[[dict], None] — sub-tables, linked items
    on_edit=None,                          # Callable[[dict], None] — Edit button clicked
    on_deleted=None,                       # Callable[[], None] — called after successful delete
    show_edit=True,
    show_delete=True,
)
```

**Methods:**
- `detail.set_item(item)` — set the item to display
- `await detail.build()` — render the card

**Layout:** summary section + action buttons (Edit/Delete) + optional related section.

No observer integration — the caller (ViewStack or page-level) handles refresh.

### `Dialog`

Positioned card overlay. Context manager for building dialog content.

```python
with Dialog(
    state=None,                            # dict | None — key: is_open
    title=None,                            # str — auto-generates header with close button
    dialog_class="",                       # additional CSS class
    on_close=None,                         # Callable — called when dialog closes
) as dlg:
    # Dialog body content here
    ui.input("Name")

    with dlg.actions():                    # Footer action buttons
        Button("Save", on_click=handle_save)
        Button("Cancel", color="secondary", on_click=dlg.close)
```

**Methods:**
- `dlg.open()` / `dlg.close()`
- `dlg.actions()` — context manager for footer buttons

**State keys:** `is_open: bool`, `title: str` (if title provided)

ESC key closes the dialog. Dialog DOM is attached to client root layout (survives refreshable rebuilds).

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

**Navigation methods:**
- `vs.show_list()` — navigate to list view
- `vs.show_detail(item)` — navigate to detail view
- `vs.show_edit_existing(item=None)` — edit current or specified item
- `vs.show_edit_new()` — edit form for new item
- `vs.go_back()` — edit->detail or detail/edit->list

**Properties:** `vs.view` (str), `vs.item` (dict | None)

**State keys:** `view: str` ("list", "detail", "edit"), `item: dict | None`

The list panel is rendered once with binding-driven visibility — the list component's store observer stays alive while navigating to detail/edit.

### `Tabs`

Tab bar with pre-rendered panels, toggled via bindings.

```python
tabs = Tabs(
    tabs=[                                 # list of (key, label, async render callback)
        ("guests", "Guests", render_guests),
        ("admins", "Admins", render_admins),
    ],
    state=None,                            # dict | None — key: active
)
await tabs.build()
```

**State keys:** `active: str` (defaults to first tab's key)

---

## Wizard

### `WizardStep`

Defines a single step in a wizard.

```python
WizardStep(
    name: str,                             # step identifier
    title: str,                            # displayed title
    render: Callable[[dict], Awaitable],   # async render function, receives wizard state
    validate: Callable[[dict], bool] | None,  # return True if step is valid
    next_label: str = "Next ->",           # customizable button labels
    back_label: str = "<- Back",
)
```

### `StepWizard`

Multi-step wizard dialog.

```python
wizard = StepWizard(
    steps=[WizardStep(...)],               # list of steps
    on_complete=handle_complete,           # async Callable[[dict], None] — receives final state
    cancel_label="Cancel",
    complete_label="Create",               # label for final step's button
)
await wizard.show()                        # opens dialog
```

**Properties:** `wizard.state` (dict), `wizard.current_step`, `wizard.is_first_step`, `wizard.is_last_step`

---

## Buttons & Layout

### `Button`

RDM-styled button. Maps `color` to `rdm-btn-{color}` CSS class.

```python
Button(text="", on_click=None, color="primary")  # "primary", "secondary", "danger", etc - see ng_rdm.css
```

### `IconButton`

Icon-only button using Bootstrap Icons.

```python
IconButton(icon="pencil", on_click=None, color="primary", tooltip="Edit")
```

### `Icon`

Standalone icon using Bootstrap Icons.

```python
Icon(icon="check", on_click=None, color="primary", tooltip="Done")
```

### `Row`

Flex row container without spurious div's.

```python
with Row(gap="1rem", align="center", classes="", style=""):
    Button("A")
    Button("B")
```

### `Col`

Flex column container without spurious div's.

```python
with Col(gap="1rem", classes="", style=""):
    ...
```

### `Separator`

Horizontal rule with `rdm-separator` styling.

```python
Separator(classes="", style="")
```

---

## Utilities

### `confirm_dialog()`

Shows a confirmation dialog. Returns `True` if confirmed, `False` if cancelled.

```python
result = await confirm_dialog(
    item=None,                             # dict — for format string substitution
    prompts=None,                          # dict with keys: question, explanation, yes_button, no_button
)
```

Default prompts are for delete confirmation. Values can use `{field_name}` format strings filled from `item`.

### Localization

```python
set_language("nl_nl")                      # set language (built-in: "en_gb", "nl_nl")
set_translations({"nl_nl": {"Save": "Opslaan"}})  # extend/override translations
_(key)                                     # translate a string
none_as_text(value)                        # format empty/None as translated "(none)"
```

---

## Getting Started — Wiring Up a New App

Minimal recipe for a new ng_rdm application: define a model, initialize the database, create a store, and render a page.

### 1. Define a Tortoise model

Extend `QModel` (ng_rdm's Tortoise Model subclass). Add `field_specs` for validation.

```python
from tortoise import fields
from ng_rdm.models import QModel, FieldSpec, Validator

class Product(QModel):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    price = fields.DecimalField(max_digits=10, decimal_places=2)

    field_specs = {
        "name": FieldSpec(validators=[
            Validator(message="Name is required", validator=lambda v, _: bool(v and v.strip()))
        ]),
        "price": FieldSpec(validators=[
            Validator(message="Price must be positive", validator=lambda v, _: float(v) > 0 if v else False)
        ]),
    }

    class Meta(QModel.Meta):
        table = "product"
```

### 2. Initialize DB + stores (module level)

Call `init_db` at module level (before any page renders). Shutdown is handled automatically.

```python
from pathlib import Path
from nicegui import app
from ng_rdm.store import TortoiseStore, init_db

DB_PATH = Path(__file__).parent / "app.sqlite3"
init_db(app, f"sqlite://{DB_PATH}", modules={"models": [__name__]}, generate_schemas=True)

product_store = TortoiseStore(Product)
```

- `modules` maps a label to a list of Python module paths containing your QModel classes.
- `generate_schemas=True` auto-creates tables — handy for dev, skip in production.
- For in-memory prototyping without a database, use `DictStore()` instead.

### 3. Render a page

```python
from nicegui import ui
from ng_rdm.components import rdm_init, Column, TableConfig, FormConfig, ActionButtonTable, EditDialog

@ui.page("/")
async def index():
    rdm_init()  # load CSS + icons — call once per page

    table_config = TableConfig(columns=[
        Column(name="name", label="Name", width_percent=60),
        Column(name="price", label="Price", width_percent=40, ui_type=ui.number),
    ])
    form_config = FormConfig(columns=table_config.columns, title_add="New Product", title_edit="Edit Product")

    dlg = EditDialog(data_source=product_store, config=form_config,
                     on_saved=lambda _: table.build.refresh())
    table = ActionButtonTable(
        data_source=product_store, config=table_config,
        on_add=dlg.open_for_new, on_edit=dlg.open_for_edit,
    )
    await table.build()

ui.run(title="My App")
```

### Key points

- **One store per model** — `TortoiseStore(ModelClass)` handles CRUD, validation, and observer notifications.
- **Stores are shared singletons** — create them at module level, reuse across pages.
- **`rdm_init()` per page** — loads Bootstrap Icons CDN and `ng_rdm.css`. Call it once at the top of each `@ui.page` function.
- **Components take a `data_source`** — pass any store (or custom `RdmDataSource` implementation).
- **`DictStore`** — in-memory store, useful for prototyping or non-persistent data. Same API as `TortoiseStore`.
- **Foreign keys** — use `Column(name="category__name")` (double underscore) and TortoiseStore auto-joins the related model.

See `examples/catalog.py` for a full working app with multiple models, stores, and all component types.

---

## Observer Lifecycle

Components using `ObservableRdmComponent` (directly or via `ObservableRdmTable`) support:

- `observe(topics=None)` — start observing data source, with optional topic filter
- `unobserve()` — stop observing
- `reobserve(topics=None)` — update subscription topics

`ObservableRdmTable` calls `observe(topics=filter_by)` automatically when `auto_observe=True` (default). Set `auto_observe=False` for manual lifecycle control.

Auto-cleanup: when a component's DOM context is gone (e.g. page navigation), `_handle_datasource_change` auto-unobserves via `build.prune()`.

### Build pattern

```python
# Simple: just the table
await table.build()

# With toolbars (add button, custom toolbar):
await table.build_with_toolbars()

# Or call build() directly — it renders toolbars at configured position internally
```
