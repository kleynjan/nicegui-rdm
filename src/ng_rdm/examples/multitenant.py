"""
Multitenant Example — ng_rdm multitenancy with MultitenantTortoiseStore.

Two tenants ("A" and "B") share a single Products table but each get their
own store instance. Modifying data for tenant A does not impact tenant B
tables and vice versa.

Layout: four ActionButtonTables in a quadrant — upper two for tenant A,
lower two for tenant B. The left table in each pair has an Add button; both
tables in a pair react to store changes.

Run:  python -m ng_rdm.examples.multitenant
Open: http://localhost:8080
Creates: multitenant.sqlite3
"""
from pathlib import Path

from tortoise import fields
from nicegui import app, ui, Client

from ng_rdm.components import (
    rdm_init, Column, TableConfig, FormConfig,
    ActionButtonTable, EditDialog,
    Row, Col, Separator,
)
from ng_rdm.store import MultitenantTortoiseStore, init_db
from ng_rdm import mt_store_registry as store_registry
from ng_rdm.store.multitenancy import set_valid_tenants
from ng_rdm.models import QModel, FieldSpec, Validator


# =============================================================================
# Model
# =============================================================================

class Product(QModel):
    id = fields.IntField(pk=True)
    tenant = fields.CharField(max_length=10)
    name = fields.CharField(max_length=100)
    stock = fields.IntField(default=0)

    field_specs = {
        "name": FieldSpec(validators=[
            Validator(message="Name is required", validator=lambda v, _: bool(v and v.strip()))
        ])
    }

    class Meta(QModel.Meta):
        table = "mt_product"


# =============================================================================
# Database
# =============================================================================

DB_PATH = Path(__file__).parent / "multitenant.sqlite3"
init_db(app, f"sqlite://{DB_PATH}", modules={"models": [__name__]}, generate_schemas=True)


async def seed_data():
    if await Product.all().count() > 0:
        return
    for name, stock in [("Widget", 15), ("Gadget", 42), ("Gizmo", 7)]:
        await Product.create(tenant="A", name=name, stock=stock)
    for name, stock in [("Bolt", 200), ("Nut", 350), ("Washer", 500)]:
        await Product.create(tenant="B", name=name, stock=stock)


@app.on_startup
async def startup():
    set_valid_tenants(["A", "B"])
    await seed_data()
    store_registry.register_store("A", "product", MultitenantTortoiseStore(Product, tenant="A"))
    store_registry.register_store("B", "product", MultitenantTortoiseStore(Product, tenant="B"))


# =============================================================================
# Column / config definitions
# =============================================================================

table_cols = [
    Column(name="name", label="Product", width_percent=65),
    Column(name="stock", label="Stock", width_percent=25),
]

form_cols = [
    Column(name="name", label="Name", required=True),
    Column(name="stock", label="Stock", ui_type=ui.number, default_value=0),
]


# =============================================================================
# Page
# =============================================================================

@ui.page("/")
async def main(client: Client):
    rdm_init(extra_css=Path(__file__).parent / "examples.css", show_refresh_transitions=True)
    await client.connected()

    store_a = store_registry.get_store("A", "product")
    store_b = store_registry.get_store("B", "product")

    with Col(classes="demo-content-column"):
        ui.label("Multitenant Example").style("font-size: 2rem")
        ui.label(
            "Each tenant has its own store instance. Changes to Tenant A do not affect "
            "Tenant B tables and vice versa. Both tables within a tenant react to the same store."
        ).style("margin-bottom: 1.5rem")

        for tenant_label, store in [("Tenant A", store_a), ("Tenant B", store_b)]:
            ui.label(tenant_label).style("font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem")

            dialog = EditDialog(
                data_source=store,
                config=FormConfig(
                    columns=form_cols,
                    title_add=f"Add Product — {tenant_label}",
                    title_edit=f"Edit Product — {tenant_label}",
                ),
            )

            async def on_delete(row: dict, s=store):
                await s.delete_item(row)

            with Row(align="flex-start", gap="1.5rem", style="margin-bottom: 1.5rem"):
                with Col(style="flex: 1"):
                    table_left = ActionButtonTable(
                        data_source=store,
                        config=TableConfig(
                            columns=table_cols,
                            add_button=f"+ Add Product",
                        ),
                        on_add=dialog.open_for_new,
                        on_edit=dialog.open_for_edit,
                        on_delete=on_delete,
                    )
                    await table_left.build()

                with Col(style="flex: 1"):
                    table_right = ActionButtonTable(
                        data_source=store,
                        config=TableConfig(
                            columns=table_cols,
                            show_add_button=False,
                        ),
                        on_edit=dialog.open_for_edit,
                        on_delete=on_delete,
                    )
                    await table_right.build()

            Separator(style="margin-bottom: 1.5rem")


ui.run(title="Multitenant — ng_rdm", storage_secret="mt_1928")
