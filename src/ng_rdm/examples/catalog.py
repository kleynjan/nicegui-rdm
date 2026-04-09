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
    WizardStep, StepWizard, DetailCard,
    ObservableRdmComponent,
    Button,
    Row, Col, Separator,
)
from ng_rdm.store import TortoiseStore, DictStore, init_db, close_db, store_registry
from ng_rdm.models import QModel, FieldSpec, Validator
from ng_rdm.components.i18n import set_language


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
toc_store = DictStore()   # static component reference data

toc_data = [
    {"component": "ActionButtonTable", "use_case": "CRUD table",
        "key_api": "on_add, on_edit, on_delete", "anchor": "action"},
    {"component": "ListTable", "use_case": "Navigation / read-only", "key_api": "on_click(row_id)", "anchor": "list"},
    {"component": "SelectionTable", "use_case": "Bulk selection", "key_api": "selected_ids, select_all(), clear_selection()",
     "anchor": "selection"},
    {"component": "EditCard", "use_case": "In-place form",
        "key_api": "set_item(item|None), on_saved, on_cancel", "anchor": "editcard"},
    {"component": "EditDialog", "use_case": "Modal form", "key_api": "open_for_new(), open_for_edit(item)",
     "anchor": "action"},
    {"component": "Dialog", "use_case": "Generic modal",
        "key_api": "open(), close(), state['is_open']", "anchor": "dialog"},
    {"component": "Tabs", "use_case": "Content sections",
        "key_api": "state['active'], visibility-toggled panels", "anchor": "tabs"},
    {"component": "ViewStack", "use_case": "List → detail → edit",
        "key_api": "show_list/detail/edit_new/edit_existing()", "anchor": "viewstack"},
    {"component": "StepWizard", "use_case": "Multi-step form",
        "key_api": "WizardStep(render, validate), on_complete", "anchor": "wizard"},
    {"component": "ObservableRdmComponent", "use_case": "Custom reactive UI",
        "key_api": "observe(), @ui.refreshable_method build()", "anchor": "custom"},
]

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
    if not await toc_store.read_items():
        for item in toc_data:
            await toc_store.create_item(item)

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

async def section_toc_table():
    toc_cols = [
        Column(name="component", label="component", width_percent=28),
        Column(name="use_case", label="use case", width_percent=32),
        Column(name="key_api", label="key API", width_percent=40),
    ]

    async def on_click(row_id: int | None):
        if row_id is None:
            return
        item = await toc_store.read_item_by_id(row_id)
        if item:
            ui.navigate.to(f"#{item['anchor']}")

    ui.label("Table of Contents").classes("demo-section-heading")

    table = ListTable(
        data_source=toc_store,
        config=TableConfig(columns=toc_cols, show_add_button=False),
        on_click=on_click,
        auto_observe=False,
    )
    await table.build()


async def section_action_button_table(product_store, category_store):
    ui.label("ActionButtonTable").classes("demo-section-heading")
    ui.markdown("**Use case:** Primary CRUD interface. Edit/delete per row, add at top or bottom.")

    categories = await category_store.read_items()
    cat_options = {c["id"]: c["name"] for c in categories}
    form_cols = [
        Column(name="category_id", label="Category", ui_type=ui.select, parms={"options": cat_options}),
        *product_form_cols,
    ]

    dialog = EditDialog(
        data_source=product_store,
        config=FormConfig(columns=form_cols, title_add="Add Product", title_edit="Edit Product"),
    )

    async def on_delete(row: dict):
        await product_store.delete_item(row)

    table = ActionButtonTable(
        data_source=product_store,
        config=TableConfig(
            columns=product_cols,
            add_button="+ Add Product",
            custom_actions=[
                RowAction(icon="eye", tooltip="Inspect", color="default", callback=lambda row: ui.notify(str(row))),
            ],
        ),
        on_add=dialog.open_for_new,
        on_edit=dialog.open_for_edit,
        on_delete=on_delete,
    )
    await table.build()


async def section_list_table(category_store):
    ui.label("ListTable").classes("demo-section-heading")
    ui.markdown("**Use case:** Navigation lists, master-detail (e.g, in viewstack). Click and forget: no persistent state.")

    selected_label = ui.label("Click a row").classes("demo-caption")

    async def on_click(row_id: int | None):
        items = await category_store.read_items(filter_by={"id": row_id})
        if items:
            selected_label.text = f"Selected: {items[0]['name']}"

    table = ListTable(
        data_source=category_store,
        config=TableConfig(columns=category_cols, show_add_button=False, empty_message="No categories"),
        on_click=on_click,
    )
    await table.build()


async def section_selection_table(selection_state, product_store):
    ui.label("SelectionTable").classes("demo-section-heading")
    ui.markdown("**Use case:** Multi-select, eg for bulk operations.")

    def render_toolbar():
        def handle_multi_select_change():
            if not selection_state["multi_select"]:
                table.clear_selection()
        Button("Select All", on_click=table.select_all).bind_enabled_from(selection_state, "multi_select")
        Button("Clear", color="secondary", on_click=table.clear_selection)
        ui.checkbox("Multi-select", on_change=handle_multi_select_change).bind_value(selection_state, "multi_select")
        ui.checkbox("Show checkboxes", on_change=table.build.refresh).bind_value(selection_state, "show_checkboxes")

    table = SelectionTable(
        state=selection_state,
        data_source=product_store,
        config=TableConfig(columns=product_cols, show_add_button=False),
        show_checkboxes=True,
        multi_select=False,
        render_toolbar=render_toolbar,
    )
    await table.build_with_toolbars()

    ui.label("").classes("demo-caption").bind_text_from(
        selection_state, "selected_ids",
        backward=lambda ids: f"{len(ids)} selected" if ids else "None selected",
    )


async def section_edit_card(category_store):
    ui.label("EditCard").classes("demo-section-heading")
    ui.markdown("**Use case:** In-place editing inside a ViewStack edit view or standalone form.")

    items = await category_store.read_items()
    item = items[0] if items else None

    saved_label = ui.label("").classes("demo-caption")

    edit = EditCard(
        data_source=category_store,
        config=FormConfig(columns=category_form_cols, title_edit="Edit Category"),
        on_saved=lambda saved: saved_label.set_text(f"Saved: {saved['name']}"),
        on_cancel=lambda: saved_label.set_text("Cancelled"),
    )
    edit.set_item(item)
    await edit.build()


def section_dialog(dialog):
    ui.label("Dialog").classes("demo-section-heading")
    ui.markdown("**Use case:** Confirmations, focused interactions.")

    with Dialog(state=dialog, title="Confirm Action") as dlg:
        # ui.label("Confirm Action").classes("rdm-dialog-title")
        ui.label("Are you sure you want to proceed?")
        with dlg.actions():
            Button("Confirm", on_click=dlg.close)
            Button("Cancel", color="secondary", on_click=dlg.close)

    with Row():
        Button("Open Dialog", on_click=dlg.open)
        # External state control: open via state dict
        Button("Open via state", color="secondary", on_click=lambda: dlg.open())
        status = ui.label("").classes("demo-caption")
        status.bind_text_from(dialog, "is_open",
                              backward=lambda v: "open" if v else "closed")


async def section_tabs(tabs, product_store, category_store):
    ui.label("Tabs").classes("demo-section-heading")
    ui.markdown("**Use case:** Multiple panels with tab navigation. Content is rendered upfront; visibility is toggled.")

    async def render_products():
        config = TableConfig(
            columns=product_cols[:2],
            show_add_button=False, show_edit_button=False, show_delete_button=False,
        )
        table = ListTable(data_source=product_store, config=config)
        await table.build()

    async def render_categories():
        config = TableConfig(
            columns=category_cols,
            show_add_button=False, show_edit_button=False, show_delete_button=False,
        )
        table = ListTable(data_source=category_store, config=config)
        await table.build()

    async def render_about():
        ui.label("ng_rdm — Reactive Data Management for NiceGUI")
        ui.label("Components are state-driven, protocol-based, and store-agnostic.").classes("rdm-text-muted")

    tabs_widget = Tabs(state=tabs, tabs=[
        ("products", "Products", render_products),
        ("categories", "Categories", render_categories),
        ("about", "About", render_about),
    ])
    await tabs_widget.build()

    with Row():
        ui.label("Current state:")
        ui.label("").bind_text_from(tabs, "active").style("font-style: italic;")

    with Row(style="margin-top: 0.5rem"):
        def open_tab(key: str):
            tabs["active"] = key

        ui.label("Switch tabs by modifying state:")
        # External state control: switch tabs by modifying state directly
        for key, label in [("products", "→ Products"), ("categories", "→ Categories"), ("about", "→ About")]:
            Button(label, color="secondary", on_click=lambda _, k=key: open_tab(k))


async def section_viewstack(viewstack, vs_list, detail_card, vs_editcard, category_store, product_store):
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
            state=detail_card,
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
            state=vs_editcard,
            data_source=category_store,
            config=edit_form,
            on_saved=lambda saved: vs.show_detail(saved),
            on_cancel=lambda: vs.show_detail(item) if item else vs.show_list(),
        )
        edit.set_item(item)
        await edit.build()

    stack = ViewStack(
        state=viewstack,
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

    def __init__(self, data_source, highlight_field: str, highlight_values: set, state: dict | None = None):
        super().__init__(data_source=data_source, state=state)
        self.highlight_field = highlight_field
        self.highlight_values = highlight_values
        self.observe()

    @ui.refreshable_method
    async def build(self):
        await self.load_data()
        with html.div().classes("rdm-component show-refresh rdm-table-card"):
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

async def section_custom_component(highlight):
    ui.label("Custom Component (ObservableRdmComponent)").classes("demo-section-heading")
    ui.markdown(
        """
1. Subclass and instantiate a ObservableRdmComponent, automatically observing the store
2. Implement @ui.refreshable_method build()
3. Call self.load_data()
4. If store data changes, build.refresh() is automatically triggered, UI is updated"""
    )

    highlight_table = HighlightTable(
        data_source=task_store,
        highlight_field="priority",
        highlight_values={"high"},
        state=highlight,
    )
    await highlight_table.build()

    with Row(style="margin-top: 0.5rem; font-style: italic;"):
        ui.label("High-priority rows are highlighted.")

    with Row(style="margin-top: 1.5rem; font-weight: 500;"):
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

        Button("Toggle Task #2", color="secondary", on_click=modify_task)

# =============================================================================
# Main page
# =============================================================================

@ui.page("/")
async def main(client: Client):

    def _section_card(anchor: str):
        return html.div().classes(f"catalog-section catalog-section-{anchor}").props(f'id={anchor}')

    rdm_init(extra_css=Path(__file__).parent / "examples.css", show_refresh_transitions=True)
    set_language("en_gb")
    await client.connected()

    # component state in app.storage.user => persistence across refreshes
    ui_state = app.storage.user.setdefault("ui_state", {
        "selection": {'multi_select': True, 'show_checkboxes': True, 'selected_ids': []},
        "dialog": {},
        "tabs": {},
        "viewstack": {}, "vs_list": {}, "vs_editcard": {}, "detail_card": {},
        "highlight": {},
    })

    product_store = store_registry.get_store("default", "product")
    category_store = store_registry.get_store("default", "category")

    with Col(classes="demo-content-column"):

        ui.label("Taming Quasar: ng_rdm components showcase").style("font-size: 2rem")
        ui.label("(1) Build composite widgets (like tables) with straight html & css")
        ui.label("(2) For the rest: restyle the hell out of it").style("margin-bottom: 1rem")

        with _section_card("toc"):
            await section_toc_table()

        Separator()

        with _section_card("action"):
            await section_action_button_table(product_store, category_store)

        with _section_card("list"):
            await section_list_table(category_store)

        with _section_card("selection"):
            await section_selection_table(ui_state["selection"], product_store)

        with _section_card("editcard"):
            await section_edit_card(category_store)

        with _section_card("dialog"):
            section_dialog(ui_state["dialog"])

        with _section_card("tabs"):
            await section_tabs(ui_state["tabs"], product_store, category_store)

        with _section_card("viewstack"):
            await section_viewstack(ui_state["viewstack"], ui_state["vs_list"], ui_state["detail_card"], ui_state["vs_editcard"], category_store, product_store)

        with _section_card("wizard"):
            await section_wizard(product_store, category_store)

        with _section_card("custom"):
            await section_custom_component(ui_state["highlight"])

        Separator(style="margin-top: 2rem;")

        ui.label("Return to top").classes(
            "demo-caption").style("cursor: pointer;").on("click", lambda: ui.navigate.to("#toc"))

ui.run(title="ng_rdm Component Catalog", storage_secret="catalog_1928")
