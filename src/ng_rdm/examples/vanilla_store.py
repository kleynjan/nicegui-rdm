"""
Store layer with vanilla NiceGUI components.

Demonstrates the ng_rdm store/observer pattern WITHOUT any RDM UI components.
Uses plain ui.table, ui.input, ui.button, and @ui.refreshable.

Two side-by-side product tables are each subscribed to a single category topic:
editing Electronics doesn't refresh the Clothing table, and vice versa.
An event log makes the selective notification visible in real-time.

Run:  python -m ng_rdm.examples.vanilla_store
Open: http://localhost:8080
No rdm_init() call — the store layer is entirely independent of RDM components.
"""
from nicegui import app, ui, Client

from ng_rdm import DictStore, store_registry
from ng_rdm.store import StoreEvent
from ng_rdm.components import Row, Col, Separator, Button


# =============================================================================
# Store setup  (module-level singleton)
# =============================================================================

store = DictStore()
store.set_topic_fields(["category"])
store_registry.register_store("demo", "products", store)

SEED = [
    {"name": "Laptop Pro", "price": 1299.0, "category": "Electronics"},
    {"name": "Wireless Headphones", "price": 299.0, "category": "Electronics"},
    {"name": "T-Shirt Classic", "price": 24.99, "category": "Clothing"},
    {"name": "Jeans Standard", "price": 59.99, "category": "Clothing"},
]

CATEGORIES = ["Electronics", "Clothing"]


@app.on_startup
async def startup():
    if not await store.read_items():
        for item in SEED:
            await store.create_item(item)


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

    with Col(gap="1rem", style="width: 100%; max-width: 64rem; margin: 0 auto; padding: 1rem"):
        ui.label("Store + Vanilla NiceGUI").classes("demo-section-heading")
        ui.markdown(
            "No RDM components — `@ui.refreshable` sections are triggered by store observers. "
            "Edit a product and watch only the matching category panel refresh."
        )

        # ── two side-by-side category panels ──────────────────────────────────

        observers: list = []  # track for cleanup on disconnect

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

            async def on_category_change(event: StoreEvent):
                await panel.refresh()

            store.add_observer(on_category_change, topics={"category": category})
            observers.append(on_category_change)

        with Row(gap="2rem", style="width: 100%"):
            for cat in CATEGORIES:
                with Col(style="flex: 1"):
                    await build_category_panel(cat)

        # ── edit form ─────────────────────────────────────────────────────────

        Separator()
        ui.label("Edit a product").classes("demo-subtitle")

        with Row(align="flex-end", style="flex-wrap: wrap"):
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

            Button("Save", on_click=save_edit)

        # ── add form ──────────────────────────────────────────────────────────

        Separator()
        ui.label("Add a product").classes("demo-subtitle")

        with Row(align="flex-end", style="flex-wrap: wrap"):
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

            Button("Add", on_click=add_product)

        # ── event log ─────────────────────────────────────────────────────────

        Separator()
        ui.label("Store event log").classes("demo-subtitle")
        ui.label("Every observer receives events scoped to its topic.").classes("demo-caption")

        log = ui.log(max_lines=25).style("width: 100%; height: 160px; font-size: 0.85rem;")

        async def on_any_event(event: StoreEvent):
            cat = event.item.get("category", "?")
            name = event.item.get("name", "?")
            log.push(f"[{event.verb.upper()}] {name!r}  category={cat!r}")

        store.add_observer(on_any_event)
        observers.append(on_any_event)

    # cleanup observers when client disconnects (store is a singleton)
    async def cleanup():
        for obs in observers:
            store.remove_observer(obs)

    client.on_disconnect(cleanup)


ui.run(title="Vanilla Store — ng_rdm", port=8080)
