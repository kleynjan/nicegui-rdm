"""
Store layer with vanilla NiceGUI components.

Demonstrates the ng_rdm store/observer pattern WITHOUT any RDM UI components.
Uses plain ui.table, ui.input, ui.button, and @ui.refreshable.

Two side-by-side product tables are each subscribed to a single category topic:
editing Electronics doesn't refresh the Clothing table, and vice versa.

Run:  python -m ng_rdm.examples.vanilla_store
Open: http://localhost:8080
No rdm_init() call — the store layer is entirely independent of RDM components.
"""
from pathlib import Path

from nicegui import app, ui, Client
from tortoise import fields

from ng_rdm.store import TortoiseStore, init_db, store_registry
from ng_rdm.models import RdmModel


# =============================================================================
# Model
# =============================================================================

class Product(RdmModel):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    price = fields.FloatField()
    category = fields.CharField(max_length=50)

    class Meta(RdmModel.Meta):
        table = "vanilla_product"


# =============================================================================
# Database + store setup  (module-level)
# =============================================================================

DB_PATH = Path(__file__).parent / "vanilla_store.sqlite3"
init_db(app, f"sqlite://{DB_PATH}", modules={"models": [__name__]}, generate_schemas=True)

SEED = [
    {"name": "Laptop Pro", "price": 1299.0, "category": "Electronics"},
    {"name": "Wireless Headphones", "price": 299.0, "category": "Electronics"},
    {"name": "T-Shirt Classic", "price": 24.99, "category": "Clothing"},
    {"name": "Jeans Standard", "price": 59.99, "category": "Clothing"},
]

CATEGORIES = ["Electronics", "Clothing"]


async def seed_data():
    if await Product.all().count() > 0:
        return
    for item in SEED:
        await Product.create(**item)


@app.on_startup
async def startup():
    await seed_data()
    store = TortoiseStore(Product)
    store.set_topic_fields(["category"])
    store_registry.register_store("products", store)


# =============================================================================
# Page
# =============================================================================

TABLE_COLUMNS = [
    {"name": "id", "label": "ID", "field": "id"},
    {"name": "name", "label": "Name", "field": "name"},
    {"name": "price", "label": "Price", "field": "price"},
]


@ui.page("/")
async def main(client: Client):
    await client.connected()

    store = store_registry.get_store("products")

    with ui.column().style("gap: 1rem; width: 100%; max-width: 64rem; margin: 0 auto; padding: 1rem"):
        ui.label("Store + Vanilla NiceGUI").classes("demo-section-heading")
        ui.markdown(
            "No RDM components — `@ui.refreshable` sections are triggered by store observers. "
            "Edit a product and watch only the matching category panel refresh."
        )

        # ── two side-by-side category panels ──────────────────────────────────

        async def build_category_panel(category: str):
            ui.label(category).style("font-size: 1rem; font-weight: 600")

            @ui.refreshable
            async def panel():
                items = await store.read_items(filter_by={"category": category})
                rows = [
                    {"id": i["id"], "name": i["name"], "price": f"${i['price']:.2f}"}
                    for i in items
                ]
                ui.table(columns=TABLE_COLUMNS, rows=rows, row_key="id").style("width: 100%")

            await panel()

            async def on_category_change(_event):  # StoreEvent
                panel.prune()
                if not panel.targets:
                    store.remove_observer(on_category_change)
                    return
                await panel.refresh()

            store.add_observer(on_category_change, topics={"category": category})

        with ui.row().style("gap: 2rem; width: 100%"):
            for cat in CATEGORIES:
                with ui.column().style("flex: 1"):
                    await build_category_panel(cat)

        # ── edit form ─────────────────────────────────────────────────────────

        ui.separator()
        ui.label("Edit a product").classes("demo-subtitle")

        with ui.row().style("align-items: flex-end; flex-wrap: wrap"):
            items_now = await store.read_items()
            options = {i["id"]: f"{i['name']} ({i['category']})" for i in items_now}
            item_select = ui.select(options, label="Product", value=next(iter(options), None))
            name_input = ui.input("New name")

            async def save_edit():
                if item_select.value is None or not name_input.value.strip():
                    ui.notify("Select a product and enter a name", type="warning")
                    return
                await store.update_item(item_select.value, {"name": name_input.value.strip()})
                name_input.set_value("")

            ui.button("Save", on_click=save_edit)

        # ── add form ──────────────────────────────────────────────────────────

        ui.separator()
        ui.label("Add a product").classes("demo-subtitle")

        with ui.row().style("align-items: flex-end; flex-wrap: wrap"):
            new_name = ui.input("Name")
            new_price = ui.number("Price", min=0, value=0)
            new_cat = ui.select(CATEGORIES, label="Category", value=CATEGORIES[0])

            async def add_product():
                if not new_name.value.strip():
                    ui.notify("Name is required", type="warning")
                    return
                await store.create_item({
                    "name": new_name.value.strip(),
                    "price": float(new_price.value or 0),
                    "category": new_cat.value,
                })
                new_name.set_value("")
                new_price.set_value(0)

            ui.button("Add", on_click=add_product)


ui.run(title="Vanilla Store — ng_rdm")
