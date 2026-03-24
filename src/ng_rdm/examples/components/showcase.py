"""
ng_rdm Component Showcase - Tutorial for New Users
=====================================================

A practical introduction to ng_rdm components, demonstrating
each component type with a real SQLite database.

Run from project root:
    python -m ng_rdm.examples.components.showcase

Then open http://localhost:8080 in your browser.
Creates: showcase.sqlite3

Components demonstrated:
- DataTable: Editable table with modal add/edit dialogs
- ListTable: Read-only clickable rows for navigation
- SelectionTable: Multi-select with checkboxes
- ViewStack: Master-detail navigation pattern
- Dialog: Modal overlay
- Tabs: Tab-based content switching

Key concepts demonstrated:
- StoreRegistry: Singleton store pattern for cross-session reactivity
- Observer pattern: Components auto-observe by default, or use explicit observe()/unobserve()
"""

from pathlib import Path
from tortoise import fields
from nicegui import app, ui
from ng_rdm.components import (
    rdm_init, Column, TableConfig,
    DataTable, ListTable, SelectionTable,
    ViewStack, Dialog, Tabs, Button,
)
from ng_rdm.store import TortoiseStore, init_db, close_db, store_registry
from ng_rdm.models import QModel, FieldSpec, Validator


# =============================================================================
# Models - Define your data structure with Tortoise ORM
# =============================================================================

class Category(QModel):
    """Product category."""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    description = fields.TextField(null=True)

    field_specs = {
        'name': FieldSpec(validators=[
            Validator(message="Name is required", validator=lambda v, _: bool(v and v.strip()))
        ])
    }

    class Meta:
        table = "showcase_category"


class Product(QModel):
    """Product with FK to Category."""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    stock = fields.IntField(default=0)
    active = fields.BooleanField(default=True)
    category: fields.ForeignKeyRelation[Category] = fields.ForeignKeyField(
        "models.Category", related_name="products", source_field="category_id"
    )

    field_specs = {
        'name': FieldSpec(validators=[
            Validator(message="Name is required", validator=lambda v, _: bool(v and v.strip()))
        ]),
        'price': FieldSpec(validators=[
            Validator(message="Price must be positive", validator=lambda v, _: float(v) > 0 if v else False)
        ])
    }

    class Meta:
        table = "showcase_product"


# =============================================================================
# Database Setup
# =============================================================================

DB_PATH = Path(__file__).parent / "showcase.sqlite3"
DB_URL = f"sqlite://{DB_PATH}"

init_db(app, DB_URL, modules={"models": [__name__]}, generate_schemas=True)
app.on_shutdown(close_db)


async def seed_data():
    """Seed sample data if database is empty."""
    if await Category.all().count() > 0:
        return

    electronics = await Category.create(name="Electronics", description="Gadgets and devices")
    clothing = await Category.create(name="Clothing", description="Apparel and accessories")
    books = await Category.create(name="Books", description="Reading materials")

    # One product per category - keep it minimal for demo clarity
    await Product.create(name="Laptop Pro", price=1299.00, stock=15, category=electronics)
    await Product.create(name="T-Shirt Classic", price=24.99, stock=200, category=clothing)
    await Product.create(name="Python Cookbook", price=49.99, stock=30, category=books)


@app.on_startup
async def startup():
    await seed_data()

    # =============================================================================
    # STORE REGISTRY - Singleton Pattern for Cross-Session Reactivity
    # =============================================================================
    # Stores must be registered at server startup as singletons.
    # This ensures all browser sessions share the same store instance,
    # enabling real-time reactivity: when one user modifies data,
    # all connected users see the update automatically.
    #
    # Without this pattern, each page request would create its own store,
    # and observers in different sessions would not be notified of changes.
    # =============================================================================
    store_registry.register_store("default", "category", TortoiseStore(Category))
    store_registry.register_store("default", "product", TortoiseStore(Product))


# =============================================================================
# Column Configurations
# =============================================================================

product_columns = [
    Column(name="name", label="Product", width_percent=30),
    Column(name="price", label="Price", width_percent=15,
           formatter=lambda x: f"${float(x):.2f}" if x else "$0.00"),
    Column(name="stock", label="Stock", width_percent=15),
    Column(name="active", label="Active", width_percent=10,
           formatter=lambda x: "✓" if x else "✗"),
]

category_columns = [
    Column(name="name", label="Category", width_percent=30),
    Column(name="description", label="Description", width_percent=60),
]


# =============================================================================
# Demo Sections
# =============================================================================

async def demo_datatable(product_store):
    """DataTable - Editable table with modal dialogs."""
    ui.label("DataTable").classes("text-h5")
    ui.markdown("""
    **Use case:** Primary editing interface for CRUD operations.
    - Click **+ Add** to create new items via modal dialog
    - Click **Edit** button on any row to modify
    - Click **Delete** to remove items
    """)

    # Reactivity test instructions
    with ui.element("div").classes("q-pa-sm q-mb-sm").style("background: #e3f2fd; border-radius: 4px;"):
        ui.label("🔄 Test Cross-Session Reactivity:").classes("text-weight-bold")
        ui.label("1. Click 'Open Second Window' below").classes("text-caption")
        ui.label("2. Add or edit a product in one window").classes("text-caption")
        ui.label("3. Watch the table update automatically in the other window!").classes("text-caption")

    ui.link("↗ Open Second Window", target="/").props("target=_blank").classes(
        "rdm-btn rdm-btn-secondary q-mb-sm")

    config = TableConfig(
        columns=product_columns,
        add_button="+ Add Product",
        show_add_button=True,
        show_edit_button=True,
        show_delete_button=True,
        dialog_title_add="Add New Product",
        dialog_title_edit="Edit Product",
    )

    # auto_observe=True (default): component observes store with filter_by as topics
    # For explicit control: DataTable(..., auto_observe=False) then table.observe(topics={...})
    table = DataTable(state={}, data_source=product_store, config=config)
    table.render_add_button()
    await table.build()


async def demo_listtable(category_store):
    """ListTable - Read-only clickable rows."""
    ui.label("ListTable").classes("text-h5")
    ui.markdown("""
    **Use case:** Navigation lists, master-detail patterns.
    - Entire row is clickable
    - No edit/delete buttons
    - Ideal for selecting items to view details
    """)

    selected = ui.label("Click a category to select").classes("text-grey")

    def on_click(row_id):
        selected.text = f"Selected category ID: {row_id}"

    config = TableConfig(columns=category_columns, empty_message="No categories")
    table = ListTable(state={}, data_source=category_store, config=config, on_click=on_click)
    await table.build()


async def demo_selectiontable(product_store):
    """SelectionTable - Multi-select with checkboxes."""
    ui.label("SelectionTable").classes("text-h5")
    ui.markdown("""
    **Use case:** Bulk operations on multiple items.
    - Checkbox column for selection
    - Select All / Clear buttons
    - Get selected IDs for batch processing
    """)

    selection_label = ui.label("No items selected").classes("text-grey")

    def on_selection_change(selected_ids):
        count = len(selected_ids)
        selection_label.text = f"Selected {count} item(s)" if count else "No items selected"

    config = TableConfig(columns=product_columns[:3], empty_message="No products")
    table = SelectionTable(
        state={}, data_source=product_store, config=config,
        on_selection_change=on_selection_change
    )
    await table.build()

    with ui.row():
        Button("Select All", on_click=lambda: table.select_all())  # type: ignore[arg-type]
        Button("Clear", on_click=lambda: table.clear_selection(), variant="secondary")  # type: ignore[arg-type]


async def demo_viewstack(category_store, product_store):
    """ViewStack - Master-detail navigation."""
    ui.label("ViewStack").classes("text-h5")
    ui.markdown("""
    **Use case:** Drill-down navigation with breadcrumbs.
    - List view → Detail view → Edit view
    - Automatic breadcrumb trail
    - Back navigation
    """)

    select_config = TableConfig(
        columns=category_columns,
        add_button="+ Add Category",
    )

    detail_config = TableConfig(
        columns=[
            Column(name="name", label="Name"),
            Column(name="description", label="Description", ui_type=ui.textarea),
        ],
    )

    async def render_detail(item: dict):
        ui.label(item.get("name", "")).classes("text-h6")
        ui.label(item.get("description", "") or "No description").classes("text-grey")

        ui.separator()
        ui.label("Products in this category:").classes("text-subtitle2")

        cat_id = item.get("id")
        if cat_id:
            products = await product_store.read_items(filter_by={"category_id": cat_id})
            if products:
                for p in products:
                    ui.label(f"• {p['name']} - ${float(p['price']):.2f}").classes("q-ml-md")
            else:
                ui.label("No products").classes("text-grey q-ml-md")

    stack = ViewStack(
        data_source=category_store,
        select_config=select_config,
        detail_config=detail_config,
        render_detail=render_detail,
        breadcrumb_root="Categories",
        item_label=lambda item: item.get("name", ""),
        show_add=True,
        show_edit=True,
        show_delete=True,
    )
    await stack.build()


def demo_dialog():
    """Dialog - Modal overlay."""
    ui.label("Dialog").classes("text-h5")
    ui.markdown("""
    **Use case:** Confirmations, forms, focused interactions.
    - Backdrop click to close
    - ESC key to close
    - Custom actions footer
    """)

    with Dialog() as dlg:
        ui.label("Confirm Action").classes("text-h6")
        ui.label("Are you sure you want to proceed?")
        with dlg.actions():
            Button("Cancel", on_click=dlg.close, variant="secondary")
            Button("Confirm", on_click=dlg.close)

    Button("Open Dialog", on_click=dlg.open)


async def demo_tabs(product_store, category_store):
    """Tabs - Tab-based content switching."""
    ui.label("Tabs").classes("text-h5")
    ui.markdown("""
    **Use case:** Organize content into switchable sections.
    - Simple tab bar with underline indicator
    - Async content rendering per tab
    """)

    async def render_products():
        config = TableConfig(columns=product_columns[:2])
        table = ListTable(state={}, data_source=product_store, config=config)
        await table.build()

    async def render_categories():
        config = TableConfig(columns=category_columns)
        table = ListTable(state={}, data_source=category_store, config=config)
        await table.build()

    async def render_about():
        ui.label("ng_rdm Component Library")
        ui.label("Build data-driven NiceGUI applications with ease.").classes("text-grey")

    tabs = Tabs([
        ("products", "Products", render_products),
        ("categories", "Categories", render_categories),
        ("about", "About", render_about),
    ])
    await tabs.build()


# =============================================================================
# Main Page
# =============================================================================

@ui.page("/")
async def main():
    rdm_init()

    ui.add_head_html("""
    <style>
        .showcase-section {
            background: white;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
    </style>
    """)

    # =============================================================================
    # RETRIEVE STORES FROM REGISTRY
    # =============================================================================
    # Get singleton store instances registered at startup.
    # All browser sessions share these same store instances, enabling reactivity.
    # =============================================================================
    product_store = store_registry.get_store("default", "product")
    category_store = store_registry.get_store("default", "category")

    with ui.column().classes("w-full max-w-4xl mx-auto q-pa-md"):
        ui.label("🎨 ng_rdm Component Showcase").classes("text-h4")
        ui.label("A tutorial introduction to ng_rdm UI components").classes("text-subtitle1 text-grey")

        ui.separator()

        # DataTable
        with ui.element("div").classes("showcase-section"):
            await demo_datatable(product_store)

        # ListTable
        with ui.element("div").classes("showcase-section"):
            await demo_listtable(category_store)

        # SelectionTable
        with ui.element("div").classes("showcase-section"):
            await demo_selectiontable(product_store)

        # Dialog
        with ui.element("div").classes("showcase-section"):
            demo_dialog()

        # Tabs
        with ui.element("div").classes("showcase-section"):
            await demo_tabs(product_store, category_store)

        # ViewStack
        with ui.element("div").classes("showcase-section"):
            await demo_viewstack(category_store, product_store)

        ui.separator()
        ui.markdown("""
        ### Quick Reference

        | Component | Use Case |
        |-----------|----------|
        | **DataTable** | Editable table with modal dialogs |
        | **ListTable** | Read-only clickable rows |
        | **SelectionTable** | Multi-select with checkboxes |
        | **ViewStack** | Master-detail navigation |
        | **Dialog** | Modal overlay |
        | **Tabs** | Tab-based navigation |
        """)


ui.run(title="ng_rdm Showcase", port=8080)
