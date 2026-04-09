"""
Master/Detail App — canonical ng_rdm pattern.

A Product → Component (bill-of-materials) application:
list view → detail view (with 1:N component sub-table) → edit view.

Structure:
  ViewStack
    List:   ListTable of products
    Detail: DetailCard with product info + ActionButtonTable of components
    Edit:   EditCard for product

Run:  python -m ng_rdm.examples.master_detail
Open: http://localhost:8080
Creates: master_detail.sqlite3
"""
from pathlib import Path

from tortoise import fields
from nicegui import app, ui, Client

from ng_rdm.components import (
    rdm_init, Column, TableConfig, FormConfig,
    ActionButtonTable, ListTable, EditCard, EditDialog,
    ViewStack, DetailCard,
    Row, Col, Separator,
)
from ng_rdm.store import TortoiseStore, init_db, close_db, store_registry
from ng_rdm.models import QModel, FieldSpec, Validator


# =============================================================================
# Models
# =============================================================================

class Product(QModel):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    stock = fields.IntField(default=0)

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
        table = "md_product"


class Component(QModel):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    quantity = fields.IntField(default=1)
    unit_cost = fields.DecimalField(max_digits=10, decimal_places=2)
    product: fields.ForeignKeyRelation[Product] = fields.ForeignKeyField(
        "models.Product", related_name="components", source_field="product_id"
    )

    field_specs = {
        "name": FieldSpec(validators=[
            Validator(message="Name is required", validator=lambda v, _: bool(v and v.strip()))
        ]),
    }

    class Meta(QModel.Meta):
        table = "md_component"


# =============================================================================
# Database
# =============================================================================

DB_PATH = Path(__file__).parent / "master_detail.sqlite3"
init_db(app, f"sqlite://{DB_PATH}", modules={"models": [__name__]}, generate_schemas=True)
app.on_shutdown(close_db)


async def seed_data():
    if await Product.all().count() > 0:
        return
    laptop = await Product.create(name="Laptop Pro", price=1299.00, stock=15)
    headphones = await Product.create(name="Wireless Headphones", price=299.00, stock=42)
    keyboard = await Product.create(name="Mechanical Keyboard", price=149.00, stock=60)

    await Component.create(name="CPU", quantity=1, unit_cost=350.00, product=laptop)
    await Component.create(name="RAM Module", quantity=2, unit_cost=45.00, product=laptop)
    await Component.create(name="SSD", quantity=1, unit_cost=120.00, product=laptop)
    await Component.create(name="Battery", quantity=1, unit_cost=80.00, product=laptop)

    await Component.create(name="Driver Unit", quantity=2, unit_cost=25.00, product=headphones)
    await Component.create(name="Bluetooth Chip", quantity=1, unit_cost=12.00, product=headphones)
    await Component.create(name="Battery", quantity=1, unit_cost=8.00, product=headphones)

    await Component.create(name="Key Switch", quantity=87, unit_cost=0.50, product=keyboard)
    await Component.create(name="PCB Board", quantity=1, unit_cost=15.00, product=keyboard)
    await Component.create(name="USB Controller", quantity=1, unit_cost=5.00, product=keyboard)


@app.on_startup
async def startup():
    await seed_data()
    store_registry.register_store("default", "product", TortoiseStore(Product))
    store_registry.register_store("default", "component", TortoiseStore(Component))


# =============================================================================
# Column / config definitions
# =============================================================================

product_list_cols = [
    Column(name="name", label="Product", width_percent=40),
    Column(name="price", label="Price", width_percent=25,
           formatter=lambda x: f"${float(x):.2f}" if x else ""),
    Column(name="stock", label="Stock", width_percent=20),
]

product_form_cols = [
    Column(name="name", label="Name", required=True),
    Column(name="price", label="Price", ui_type=ui.number),
    Column(name="stock", label="Stock", ui_type=ui.number, default_value=0),
]

component_table_cols = [
    Column(name="name", label="Component", width_percent=40),
    Column(name="quantity", label="Qty", width_percent=15),
    Column(name="unit_cost", label="Unit Cost", width_percent=20,
           formatter=lambda x: f"${float(x):.2f}" if x else ""),
]

# product_id column is hidden (ui.label = display-only, not rendered as input)
# but included so _build_item_data picks it up during save
component_form_cols = [
    Column(name="product_id", label="Product", ui_type=ui.label),
    Column(name="name", label="Name", required=True),
    Column(name="quantity", label="Quantity", ui_type=ui.number, default_value=1),
    Column(name="unit_cost", label="Unit Cost", ui_type=ui.number),
]


# =============================================================================
# Page
# =============================================================================

@ui.page("/")
async def main(client: Client):

    rdm_init(extra_css=Path(__file__).parent / "examples.css", show_refresh_transitions=True, log_file="master_detail.log")
    await client.connected()

    ui_state = app.storage.user['ui_state'] = {
        "viewstack": {}, "list_table": {}, "component_table": {},
        "editcard": {}, "component_dialog": {}, "detail_card": {},
    }

    product_store = store_registry.get_store("default", "product")
    component_store = store_registry.get_store("default", "component")

    with Col(classes="demo-content-column"):

        with Row(style="margin-bottom: 1rem"):
            ui.label("Master/detail example").classes("demo-section-heading")

        # Component EditDialog — one instance, shared across detail views
        component_dialog = EditDialog(
            state=ui_state["component_dialog"],
            data_source=component_store,
            config=FormConfig(
                columns=component_form_cols,
                title_add="Add Component",
                title_edit="Edit Component",
            ),
        )

        async def render_list(vs: ViewStack):
            async def on_click(row_id: int | None):
                items = await product_store.read_items(filter_by={"id": row_id})
                if items:
                    vs.show_detail(items[0])

            table = ListTable(
                data_source=product_store,
                config=TableConfig(
                    columns=product_list_cols,
                    add_button="+ Add Product",
                    empty_message="No products",
                    toolbar_position="bottom",
                ),
                on_click=on_click,
                on_add=vs.show_edit_new,
            )
            await table.build()

        async def render_detail(vs: ViewStack, item: dict):
            product_id = item.get("id")

            def on_add_component():
                component_dialog.open_for_new()
                # inject product_id into form state after open_for_new initialises it
                component_dialog.state["form"]["product_id"] = product_id

            async def on_delete_component(row: dict):
                await component_store.delete_item(row)

            async def render_summary(i: dict):
                ui.label(i.get("name", "")).style("font-size: 1.25rem; font-weight: 500")
                for k, v in [("Price", i.get("price")), ("Stock", i.get("stock"))]:
                    if v is not None:
                        if k == "Price":
                            v = f"${float(v):.2f}"
                        ui.label(f"{k}: {v}").classes("rdm-text-muted")

            async def render_related(_: dict):
                # Separator()
                # ui.label("Components").style("font-size: 0.875rem; font-weight: 500; margin-top: 0.5rem")
                component_table = ActionButtonTable(
                    state=ui_state["component_table"],
                    data_source=component_store,
                    config=TableConfig(
                        columns=component_table_cols,
                        add_button="+ Add Component",
                        empty_message="No components",
                        toolbar_position="bottom",
                    ),
                    filter_by={"product_id": product_id},
                    on_add=on_add_component,
                    on_edit=component_dialog.open_for_edit,
                    on_delete=on_delete_component,
                )
                await component_table.build()

            detail = DetailCard(
                state=ui_state["detail_card"],
                data_source=product_store,
                render_summary=render_summary,
                render_related=render_related,
                on_edit=lambda i: vs.show_edit_existing(i),
                on_deleted=vs.show_list,
            )
            detail.set_item(item)
            await detail.build()

        async def render_edit(vs: ViewStack, item: dict | None):
            edit = EditCard(
                state=ui_state["editcard"],
                data_source=product_store,
                config=FormConfig(
                    columns=product_form_cols,
                    title_add="New Product",
                    title_edit="Edit Product",
                ),
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


ui.run(title="Master/Detail — ng_rdm", storage_secret="md_1928")
