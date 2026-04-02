"""
ng_rdm Component Catalog

Every RDM component in one scrollable reference page. All buttons work.
Each section explains the use case and demonstrates the key API, including
how to control components via external state in app.storage.user.

Run:  python -m ng_rdm.examples.catalog
Open: http://localhost:8080
Creates: catalog.sqlite3
"""
from pathlib import Path

from tortoise import fields
from nicegui import app, ui, Client, html

from ng_rdm.components import (
    rdm_init, Column, TableConfig, FormConfig, RowAction,
    ActionButtonTable, ListTable, SelectionTable,
    EditCard, EditDialog, ViewStack, Dialog, Tabs,
    WizardStep, StepWizard, Button, DetailCard,
    ObservableRdmComponent,
    Row, Col, Separator,
)
from ng_rdm.store import TortoiseStore, DictStore, init_db, close_db, store_registry
from ng_rdm.models import QModel, FieldSpec, Validator


# =============================================================================
# Models
# =============================================================================

class Category(QModel):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    description = fields.TextField(null=True)

    field_specs = {
        "name": FieldSpec(validators=[
            Validator(message="Name is required", validator=lambda v, _: bool(v and v.strip()))
        ])
    }

    class Meta(QModel.Meta):
        table = "catalog_category"


class Product(QModel):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    stock = fields.IntField(default=0)
    expiry_date = fields.DateField(null=True)
    category: fields.ForeignKeyRelation[Category] = fields.ForeignKeyField(
        "models.Category", related_name="products", source_field="category_id"
    )

    field_specs = {
        "name": FieldSpec(validators=[
            Validator(message="Name is required", validator=lambda v, _: bool(v and v.strip()))
        ]),
        "price": FieldSpec(validators=[
            Validator(message="Price must be positive",
                      validator=lambda v, _: float(v) > 0 if v else False)
        ]),
    }

    class Meta(QModel.Meta):
        table = "catalog_product"


# =============================================================================
# Database + stores
# =============================================================================

DB_PATH = Path(__file__).parent / "catalog.sqlite3"
init_db(app, f"sqlite://{DB_PATH}", modules={"models": [__name__]}, generate_schemas=True)
app.on_shutdown(close_db)

task_store = DictStore()  # in-memory, for custom component section


async def seed_data():
    if await Category.all().count() > 0:
        return
    electronics = await Category.create(name="Electronics", description="Gadgets and devices")
    clothing = await Category.create(name="Clothing", description="Apparel and accessories")
    books = await Category.create(name="Books", description="Reading materials")
    await Product.create(name="Laptop Pro", price=1299.00, stock=15, category=electronics)
    await Product.create(name="Wireless Headphones", price=299.00, stock=42, category=electronics)
    await Product.create(name="T-Shirt Classic", price=24.99, stock=200, category=clothing)
    await Product.create(name="Python Cookbook", price=49.99, stock=30, category=books)


@app.on_startup
async def startup():
    await seed_data()
    store_registry.register_store("default", "category", TortoiseStore(Category))
    store_registry.register_store("default", "product", TortoiseStore(Product))
    if not await task_store.read_items():
        for item in [
            {"title": "Fix bug #42", "priority": "normal"},
            {"title": "Write tests", "priority": "normal"},
            {"title": "Deploy release", "priority": "high"},
            {"title": "Update docs", "priority": "normal"},
        ]:
            await task_store.create_item(item)


# =============================================================================
# Shared column / config helpers
# =============================================================================

product_cols = [
    Column(name="name", label="Product", width_percent=35),
    Column(name="price", label="Price", width_percent=18,
           formatter=lambda x: f"${float(x):.2f}" if x else ""),
    Column(name="stock", label="Stock", width_percent=12),
    Column(name="expiry_date", label="Expires", width_percent=20),
]

product_form_cols = [
    Column(name="name", label="Name", required=True),
    Column(name="price", label="Price", ui_type=ui.number),
    Column(name="stock", label="Stock", ui_type=ui.number, default_value=0),
    Column(name="expiry_date", label="Expiry Date", ui_type=ui.input, props="type=date"),
]

category_cols = [
    Column(name="name", label="Category", width_percent=35),
    Column(name="description", label="Description", width_percent=65),
]

category_form_cols = [
    Column(name="name", label="Name", required=True),
    Column(name="description", label="Description", ui_type=ui.textarea),
]


# =============================================================================
# Section renderers
# =============================================================================

async def section_action_button_table(ui_state, product_store, category_store):
    ui.label("ActionButtonTable").classes("demo-section-heading")
    ui.markdown("**Use case:** Primary CRUD interface. Edit/delete per row, add at top or bottom.")

    categories = await category_store.read_items()
    cat_options = {c["id"]: c["name"] for c in categories}
    form_cols = [
        Column(name="category_id", label="Category", ui_type=ui.select, parms={"options": cat_options}),
        *product_form_cols,
    ]

    dialog = EditDialog(
        state=ui_state["action_dialog"],
        data_source=product_store,
        config=FormConfig(columns=form_cols, title_add="Add Product", title_edit="Edit Product"),
    )

    async def on_delete(row: dict):
        await product_store.delete_item(row)

    table = ActionButtonTable(
        state=ui_state["action_table"],
        data_source=product_store,
        config=TableConfig(
            columns=product_cols,
            add_button="+ Add Product",
            custom_actions=[
                RowAction(icon="eye", tooltip="Inspect", callback=lambda row: ui.notify(str(row))),
            ],
        ),
        on_add=dialog.open_for_new,
        on_edit=dialog.open_for_edit,
        on_delete=on_delete,
    )
    await table.build()


async def section_list_table(ui_state, category_store):
    ui.label("ListTable").classes("demo-section-heading")
    ui.markdown("**Use case:** Navigation lists, master-detail (e.g, in viewstack).")

    selected_label = ui.label("Click a row").classes("demo-caption")

    async def on_click(row_id: int | None):
        items = await category_store.read_items(filter_by={"id": row_id})
        if items:
            selected_label.text = f"Selected: {items[0]['name']}"

    table = ListTable(
        state=ui_state["list_table"],
        data_source=category_store,
        config=TableConfig(columns=category_cols, show_add_button=False, empty_message="No categories"),

        on_click=on_click,
    )
    await table.build()


async def section_selection_table(ui_state, product_store):
    ui.label("SelectionTable").classes("demo-section-heading")
    ui.markdown("**Use case:** Multi-select, eg for bulk operations.")

    def render_toolbar():
        Button("Select All", on_click=table.select_all)  # type: ignore[arg-type]
        Button("Clear", on_click=table.clear_selection, variant="secondary")  # type: ignore[arg-type]

    table = SelectionTable(
        state=ui_state["selection"],
        data_source=product_store,
        config=TableConfig(
            # columns=product_cols[:3],
            columns=product_cols,
            show_add_button=False,
            show_edit_button=False,
            show_delete_button=False,
        ),
        render_toolbar=render_toolbar,
    )
    await table.build()

    count_label = ui.label("").classes("demo-caption")
    count_label.bind_text_from(
        ui_state["selection"], "selected_ids",
        backward=lambda ids: f"{len(ids)} selected" if ids else "None selected",
    )


async def section_edit_card(ui_state, category_store):
    ui.label("EditCard").classes("demo-section-heading")
    ui.markdown("**Use case:** In-place editing inside a ViewStack edit view or standalone form.")

    items = await category_store.read_items()
    item = items[0] if items else None

    saved_label = ui.label("").classes("demo-caption")

    edit = EditCard(
        state=ui_state["editcard"],
        data_source=category_store,
        config=FormConfig(columns=category_form_cols, title_edit="Edit Category"),
        on_saved=lambda saved: saved_label.set_text(f"Saved: {saved['name']}"),
        on_cancel=lambda: saved_label.set_text("Cancelled"),
    )
    edit.set_item(item)
    await edit.build()


def section_dialog(ui_state):
    ui.label("Dialog").classes("demo-section-heading")
    ui.markdown("**Use case:** Confirmations, focused interactions.")

    with Dialog(state=ui_state["dialog"]) as dlg:
        ui.label("Confirm Action").classes("demo-subtitle")
        ui.label("Are you sure you want to proceed?")
        with dlg.actions():
            Button("Cancel", on_click=dlg.close, variant="secondary")
            Button("Confirm", on_click=dlg.close)

    with Row():
        Button("Open Dialog", on_click=dlg.open)
        # External state control: open via state dict
        Button("Open via state", on_click=lambda: dlg.open(), variant="secondary")
        status = ui.label("").classes("demo-caption")
        status.bind_text_from(ui_state["dialog"], "is_open",
                              backward=lambda v: "open" if v else "closed")


async def section_tabs(ui_state, product_store, category_store):
    ui.label("Tabs").classes("demo-section-heading")
    ui.markdown("**Use case:** Multiple panels with tab navigation. Content is rendered upfront; visibility is toggled.")

    async def render_products():
        config = TableConfig(
            columns=product_cols[:2],
            show_add_button=False, show_edit_button=False, show_delete_button=False,
        )
        table = ListTable(state={}, data_source=product_store, config=config)
        await table.build()

    async def render_categories():
        config = TableConfig(
            columns=category_cols,
            show_add_button=False, show_edit_button=False, show_delete_button=False,
        )
        table = ListTable(state={}, data_source=category_store, config=config)
        await table.build()

    async def render_about():
        ui.label("ng_rdm — Reactive Data Management for NiceGUI")
        ui.label("Components are state-driven, protocol-based, and store-agnostic.").classes("rdm-text-muted")

    tabs = Tabs(state=ui_state["tabs"], tabs=[
        ("products", "Products", render_products),
        ("categories", "Categories", render_categories),
        ("about", "About", render_about),
    ])
    await tabs.build()

    with Row():
        ui.label("Current state:")
        ui.label("").bind_text_from(ui_state["tabs"], "active").style("font-style: italic;")

    with Row(style="margin-top: 0.5rem"):
        def open_tab(key: str):
            ui_state["tabs"]["active"] = key

        ui.label("Switch tabs by modifying state:")
        # External state control: switch tabs by modifying state directly
        for key, label in [("products", "→ Products"), ("categories", "→ Categories"), ("about", "→ About")]:
            Button(label, on_click=lambda k=key: open_tab(k), variant="secondary")


async def section_viewstack(ui_state, category_store, product_store):
    ui.label("ViewStack").classes("demo-section-heading")
    ui.markdown("**Use case:** List → detail → edit navigation.")

    edit_form = FormConfig(
        columns=category_form_cols,
        title_add="New Category",
        title_edit="Edit Category",
    )

    async def render_list(vs: ViewStack):
        async def on_click(row_id: int | None):
            items = await category_store.read_items(filter_by={"id": row_id})
            if items:
                vs.show_detail(items[0])

        table = ListTable(
            state=ui_state["vs_list"],
            data_source=category_store,
            config=TableConfig(
                columns=category_cols,
                add_button="+ Add Category",
                toolbar_position="bottom",
            ),
            on_click=on_click,
            on_add=vs.show_edit_new,
        )
        await table.build()

    async def render_detail(vs: ViewStack, item: dict):
        async def render_header(i: dict):
            ui.label(i.get("name", "")).classes("demo-section-heading")
            ui.label(i.get("description") or "").classes("rdm-text-muted")

        async def render_body(i: dict):
            Separator()
            ui.label("Products in this category:").style("font-size: 0.875rem; font-weight: 500; margin-top: 0.5rem")
            products = await product_store.read_items(filter_by={"category_id": i.get("id")})
            if products:
                for p in products:
                    ui.label(f"• {p['name']}  ${float(p['price']):.2f}").classes(
                        "demo-caption").style("margin-left: 1rem")
            else:
                ui.label("None").classes("rdm-text-muted demo-caption").style("margin-left: 1rem")

        detail = DetailCard(
            state=ui_state["detail_card"],
            data_source=category_store,
            render_summary=render_header,
            render_related=render_body,
            on_edit=lambda i: vs.show_edit_existing(i),
            on_deleted=vs.show_list,
        )
        detail.set_item(item)
        await detail.build()

    async def render_edit(vs: ViewStack, item: dict | None):
        edit = EditCard(
            state=ui_state["vs_editcard"],
            data_source=category_store,
            config=edit_form,
            on_saved=lambda saved: vs.show_detail(saved),
            on_cancel=lambda: vs.show_detail(item) if item else vs.show_list(),
        )
        edit.set_item(item)
        await edit.build()

    stack = ViewStack(
        state=ui_state["viewstack"],
        render_list=render_list,
        render_detail=render_detail,
        render_edit=render_edit,
    )
    await stack.build()


async def section_wizard(product_store, category_store):
    ui.label("StepWizard").classes("demo-section-heading")
    ui.markdown("**Use case:** Multi-step forms, guided flows.")

    wizard_btn_area = Row().element

    async def show_wizard():
        categories = await category_store.read_items()
        cat_options = {c["id"]: c["name"] for c in categories}

        async def step1_render(state: dict):
            ui.label("Pick a category for the new product").classes("demo-caption")
            ui.select(cat_options, label="Category", value=state.get("category_id")) \
                .bind_value(state, "category_id")

        def step1_validate(state: dict) -> bool:
            if not state.get("category_id"):
                ui.notify("Select a category", type="warning")
                return False
            return True

        async def step2_render(state: dict):
            ui.label("Fill in product details").classes("demo-caption")
            ui.input("Name").bind_value(state, "name")
            ui.number("Price", min=0).bind_value(state, "price")

        def step2_validate(state: dict) -> bool:
            if not state.get("name", "").strip():
                ui.notify("Name is required", type="warning")
                return False
            if not state.get("price"):
                ui.notify("Price is required", type="warning")
                return False
            return True

        async def on_complete(state: dict):
            await product_store.create_item({
                "name": state["name"],
                "price": float(state["price"]),
                "stock": 0,
                "category_id": state["category_id"],
            })
            ui.notify("Product created", type="positive")

        wizard = StepWizard(
            steps=[
                WizardStep(name="category", title="Step 1 — Category",
                           render=step1_render, validate=step1_validate),
                WizardStep(name="details", title="Step 2 — Product Details",
                           render=step2_render, validate=step2_validate),
            ],
            on_complete=on_complete,
        )
        await wizard.show()

    with wizard_btn_area:
        Button("Launch Wizard", on_click=show_wizard)


# Custom table component (demonstrates ObservableRdmComponent) - final section

class HighlightTable(ObservableRdmComponent):
    """Custom table that highlights rows matching a criteria.

    Extends ObservableRdmComponent: auto-observes the store and rebuilds
    on any change. Demonstrates that you can build fully custom UI while
    keeping reactivity.
    """

    def __init__(self, state: dict, data_source, highlight_field: str, highlight_values: set):
        super().__init__(state, data_source)
        self.highlight_field = highlight_field
        self.highlight_values = highlight_values
        self.observe()

    @ui.refreshable_method
    async def build(self):
        await self.load_data()
        with html.table().classes("rdm-table"):
            with html.thead():
                with html.tr():
                    for col in ["Title", "Priority"]:
                        html.th(col)
            with html.tbody():
                for row in self.data:
                    css = "rdm-selected" if row.get(self.highlight_field) in self.highlight_values else ""
                    with html.tr().classes(css):
                        html.td(row.get("title", ""))
                        html.td(row.get("priority", ""))

async def section_custom_component(ui_state):
    ui.label("Custom Component (ObservableRdmComponent)").classes("demo-section-heading")
    ui.markdown(
        """
1. Subclass and instantiate a ObservableRdmComponent, automatically observing the store
2. Implement @ui.refreshable_method build()
3. Call self.load_data()
4. If store data changes, build.refresh() is automatically triggered, UI is updated"""
    )

    highlight_table = HighlightTable(
        state=ui_state["highlight"],
        data_source=task_store,
        highlight_field="priority",
        highlight_values={"high"},
    )
    await highlight_table.build()

    with Row(style="display: block; margin-top: 0.5rem;"):
        ui.label("High-priority rows are highlighted.")
        ui.label("Try adding a task:")

    with Row(align="flex-end", style="flex-wrap: wrap"):
        title_input = ui.input("Task title")
        priority_select = ui.select(["high", "normal"], label="Priority", value="normal")

        async def add_task():
            if title_input.value.strip():
                await task_store.create_item({
                    "title": title_input.value.strip(),
                    "priority": priority_select.value,
                })
                title_input.set_value("")

        Button("Add Task", on_click=add_task)

        async def modify_task():
            items = await task_store.read_items()
            if items:
                item = items[1]
                await task_store.update_item(item["id"], {"priority": "high" if item["priority"] == "normal" else "normal"})

        Button("Toggle Task #2", on_click=modify_task)

# =============================================================================
# Main page
# =============================================================================

@ui.page("/")
async def main(client: Client):

    def _section_card(title: str):
        return html.div().classes("catalog-section")

    rdm_init(extra_css="examples.css")
    await client.connected()

    # component state in app.storage.user => persistence across refreshes
    ui_state = app.storage.user.setdefault("ui_state", {
        "action_table": {}, "action_dialog": {},
        "list_table": {},
        "selection": {},
        "editcard": {},
        "dialog": {},
        "tabs": {},
        "viewstack": {}, "vs_list": {}, "vs_editcard": {}, "detail_card": {},
        "highlight": {},
    })

    product_store = store_registry.get_store("default", "product")
    category_store = store_registry.get_store("default", "category")

    with Col(classes="demo-content-column"):
        ui.label("ng_rdm components showcase").style("font-size: 2rem")
        ui.label("No Quasar tables and dialogs, just lovely old html and css.").style("margin-bottom: 1rem")

        with _section_card("action"):
            await section_action_button_table(ui_state, product_store, category_store)

        with _section_card("list"):
            await section_list_table(ui_state, category_store)

        with _section_card("selection"):
            await section_selection_table(ui_state, product_store)

        with _section_card("editcard"):
            await section_edit_card(ui_state, category_store)

        with _section_card("dialog"):
            section_dialog(ui_state)

        with _section_card("tabs"):
            await section_tabs(ui_state, product_store, category_store)

        with _section_card("viewstack"):
            await section_viewstack(ui_state, category_store, product_store)

        with _section_card("wizard"):
            await section_wizard(product_store, category_store)

        with _section_card("custom"):
            await section_custom_component(ui_state)

        Separator()
        ui.markdown("""
        ### Quick Reference

        | Component | Use Case | Key API |
        |-----------|----------|---------|
        | **ActionButtonTable** | CRUD table | `on_add`, `on_edit`, `on_delete` |
        | **ListTable** | Navigation / read-only | `on_click(row_id)` |
        | **SelectionTable** | Bulk selection | `selected_ids`, `select_all()`, `clear_selection()` |
        | **EditCard** | In-place form | `set_item(item or None)`, `on_saved`, `on_cancel` |
        | **EditDialog** | Modal form | `open_for_new()`, `open_for_edit(item)` |
        | **Dialog** | Generic modal | `open()`, `close()`, `state["is_open"]` |
        | **Tabs** | Content sections | `state["active"]`, visibility-toggled panels |
        | **ViewStack** | List → detail → edit | `show_list/detail/edit_new/edit_existing()` |
        | **StepWizard** | Multi-step form | `WizardStep(render, validate)`, `on_complete` |
        | **ObservableRdmComponent** | Custom reactive UI | `observe()`, `@ui.refreshable_method build()` |
        """)


ui.run(title="ng_rdm Component Catalog", port=8080, storage_secret="catalog_1928")
