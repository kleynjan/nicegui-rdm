"""
nicecrud Component Showcase
===========================

A comprehensive example demonstrating all nicecrud components.
This serves as both a visual showcase and a tutorial for new users.

Run with:
    python -m ng_loba.examples.showcase

Components demonstrated:
- DataTable: Editable table with modal dialog
- ListTable: Read-only clickable rows
- ActionTable: Table with action buttons
- SelectionTable: Multi-select with checkboxes
- Tabs: Tab-based navigation
- Dialog: Modal overlay dialogs
- DetailCard / EditCard: Detail and edit views
- ViewStack: Master-detail navigation

"""
from nicegui import ui, html

# Import nicecrud components
from ng_loba.crud import (
    page_init,
    Column,
    TableConfig,
    DataTable,
    ListTable,
    ActionTable,
    SelectionTable,
    Tabs,
    Dialog,
    DetailCard,
    EditCard,
    ViewStack,
)
from ng_loba.store.base import DictStore


# =============================================================================
# Sample Data & Shared Singleton Stores
# =============================================================================
#
# IMPORTANT: For cross-browser reactivity to work, stores must be SHARED
# singletons (not recreated per page render). When one browser modifies data,
# all other browsers observing the same store instance get notified.
#
# Pattern:
#   - Create stores at module level (singleton per server process)
#   - Use getter functions to access the shared instances
#   - Stores notify all observers on create/update/delete
#   - @ui.refreshable components auto-rebuild when notified

# Sample product data
SAMPLE_PRODUCTS = [
    {"id": 1, "name": "Laptop Pro", "category": "Electronics", "price": 1299.00, "stock": 15, "status": "active"},
    {"id": 2, "name": "Wireless Mouse", "category": "Electronics", "price": 29.99, "stock": 150, "status": "active"},
    {"id": 3, "name": "USB-C Cable", "category": "Accessories", "price": 12.99, "stock": 500, "status": "active"},
    {"id": 4, "name": "Monitor 27\"", "category": "Electronics", "price": 399.00, "stock": 25, "status": "active"},
    {"id": 5, "name": "Keyboard Mechanical", "category": "Electronics", "price": 89.00, "stock": 75, "status": "low_stock"},
    {"id": 6, "name": "Webcam HD", "category": "Electronics", "price": 79.00, "stock": 0, "status": "out_of_stock"},
    {"id": 7, "name": "Headphones", "category": "Audio", "price": 199.00, "stock": 45, "status": "active"},
    {"id": 8, "name": "Mouse Pad XL", "category": "Accessories", "price": 19.99, "stock": 200, "status": "active"},
]

# Sample user data
SAMPLE_USERS = [
    {"id": 1, "name": "Alice Johnson", "email": "alice@example.com", "role": "Admin", "active": True},
    {"id": 2, "name": "Bob Smith", "email": "bob@example.com", "role": "Editor", "active": True},
    {"id": 3, "name": "Carol White", "email": "carol@example.com", "role": "Viewer", "active": True},
    {"id": 4, "name": "Dave Brown", "email": "dave@example.com", "role": "Editor", "active": False},
]


# Module-level singleton stores - shared across all browser sessions
_product_store: DictStore | None = None
_user_store: DictStore | None = None


def get_product_store() -> DictStore:
    """Get the shared singleton product store.

    Creates the store on first access, populated with sample data.
    All browsers share this same instance for cross-client reactivity.
    """
    global _product_store
    if _product_store is None:
        _product_store = DictStore()
        _product_store._items = [p.copy() for p in SAMPLE_PRODUCTS]
    return _product_store


def get_user_store() -> DictStore:
    """Get the shared singleton user store.

    Creates the store on first access, populated with sample data.
    All browsers share this same instance for cross-client reactivity.
    """
    global _user_store
    if _user_store is None:
        _user_store = DictStore()
        _user_store._items = [u.copy() for u in SAMPLE_USERS]
    return _user_store


# =============================================================================
# Column Configurations
# =============================================================================

def get_product_columns() -> list[Column]:
    """Column definitions for product tables."""
    return [
        Column(name="name", label="Product Name", width_percent=30),
        Column(name="category", label="Category", width_percent=15),
        Column(
            name="price",
            label="Price",
            width_percent=15,
            formatter=lambda x: f"${x:.2f}" if x else "$0.00",
            ui_type=ui.number,
            parms={"min": 0, "step": 0.01, "format": "%.2f"},
        ),
        Column(
            name="stock",
            label="Stock",
            width_percent=10,
            ui_type=ui.number,
            parms={"min": 0},
        ),
        Column(
            name="status",
            label="Status",
            width_percent=15,
            ui_type=ui.badge,
            parms={"color_map": {"active": "green", "low_stock": "orange", "out_of_stock": "red"}},
        ),
    ]


def get_user_columns() -> list[Column]:
    """Column definitions for user tables."""
    return [
        Column(name="name", label="Name", width_percent=25),
        Column(name="email", label="Email", width_percent=30),
        Column(name="role", label="Role", width_percent=15),
        Column(
            name="active",
            label="Status",
            width_percent=15,
            formatter=lambda x: "Active" if x else "Inactive",
        ),
    ]


# =============================================================================
# Section: DataTable Demo
# =============================================================================

async def build_datatable_demo():
    """
    DataTable Demo
    ==============

    DataTable is the primary editable table component. It displays data in a
    read-only table format with Edit/Delete buttons. Clicking Edit or the Add
    button opens a modal dialog for editing.

    Key features:
    - Native HTML <table> rendering
    - Modal dialog for add/edit operations
    - Custom cell formatters
    - Badge support for status columns
    """
    with html.div().classes("nc-component"):
        ui.label("DataTable - Editable Table with Modal Dialog").classes("text-h6 q-mb-md")
        ui.markdown("""
        **DataTable** is the primary editable component. It shows data in a table format
        with Edit/Delete buttons. Clicking buttons opens a modal dialog.
        
        ```python
        from ng_loba.crud import DataTable, Column, TableConfig
        
        config = TableConfig(
            columns=[
                Column(name="name", label="Name"),
                Column(name="price", label="Price", formatter=lambda x: f"${x:.2f}"),
            ],
            add_button="+ Add Product",
            show_edit_button=True,
            show_delete_button=True,
        )
        
        table = DataTable(state={}, data_source=store, config=config)
        await table.build()
        ```
        """)

        # Create the DataTable using shared singleton store
        store = get_product_store()
        config = TableConfig(
            columns=get_product_columns(),
            add_button="+ Add Product",
            show_add_button=True,
            show_edit_button=True,
            show_delete_button=True,
            dialog_title_add="Add New Product",
            dialog_title_edit="Edit Product",
        )

        table = DataTable(state={}, data_source=store, config=config)
        table.render_add_button()
        await table.build()


# =============================================================================
# Section: ListTable Demo
# =============================================================================

async def build_listtable_demo():
    """
    ListTable Demo
    ==============

    ListTable is a read-only table where entire rows are clickable. It's ideal
    for master-detail patterns where clicking a row navigates to a detail view.

    Key features:
    - Read-only display
    - Entire row is clickable
    - on_click callback receives row ID
    - Clean, semantic HTML
    """
    with html.div().classes("nc-component"):
        ui.label("ListTable - Clickable Row Navigation").classes("text-h6 q-mb-md")
        ui.markdown("""
        **ListTable** is a read-only table with clickable rows. Click a row to select it.
        Ideal for master-detail navigation patterns.
        
        ```python
        from ng_loba.crud import ListTable
        
        def on_row_click(row_id):
            print(f"Selected row: {row_id}")
        
        table = ListTable(
            state={},
            data_source=store,
            config=config,
            on_click=on_row_click,
        )
        await table.build()
        ```
        """)

        # Selected item display
        selected_label = ui.label("Click a row to select it").classes("nc-text-muted")

        def handle_row_click(row_id):
            selected_label.text = f"Selected user ID: {row_id}"

        # Create the ListTable using shared singleton store
        store = get_user_store()
        config = TableConfig(
            columns=get_user_columns(),
            empty_message="No users found",
        )

        table = ListTable(
            state={},
            data_source=store,
            config=config,
            on_click=handle_row_click,
        )
        await table.build()


# =============================================================================
# Section: ActionTable Demo
# =============================================================================

async def build_actiontable_demo():
    """
    ActionTable Demo
    ================

    ActionTable displays data with Edit/Delete action buttons on each row.
    Unlike DataTable, it delegates edit/delete handling to callbacks rather
    than providing built-in modal dialogs.

    Key features:
    - Read-only table display
    - Edit/Delete buttons on each row
    - Custom action handlers via callbacks
    - Configurable button labels
    """
    with html.div().classes("nc-component"):
        ui.label("ActionTable - Table with Action Buttons").classes("text-h6 q-mb-md")
        ui.markdown("""
        **ActionTable** shows data with Edit/Delete buttons. Actions are handled via callbacks
        (you implement what happens when buttons are clicked).
        
        ```python
        from ng_loba.crud import ActionTable
        
        async def on_edit(row):
            print(f"Edit: {row}")
        
        async def on_delete(row):
            print(f"Delete: {row}")
        
        table = ActionTable(
            state={},
            data_source=store,
            config=config,
            on_edit=on_edit,
            on_delete=on_delete,
        )
        await table.build()
        ```
        """)

        action_log = ui.label("Actions will appear here").classes("nc-text-muted")

        async def handle_edit(row):
            action_log.text = f"Edit clicked: {row.get('name')}"

        async def handle_delete(row):
            action_log.text = f"Delete clicked: {row.get('name')}"

        # Create the ActionTable using shared singleton store
        store = get_product_store()
        config = TableConfig(
            columns=get_product_columns()[:4],  # Exclude status for simplicity
            show_edit_button=True,
            show_delete_button=True,
        )

        table = ActionTable(
            state={},
            data_source=store,
            config=config,
            on_edit=handle_edit,
            on_delete=handle_delete,
            edit_label="Edit",
            delete_label="Delete",
        )
        await table.build()


# =============================================================================
# Section: SelectionTable Demo
# =============================================================================

async def build_selectiontable_demo():
    """
    SelectionTable Demo
    ===================

    SelectionTable adds a checkbox column for multi-select functionality.
    Selected row IDs are tracked and available via the selected_ids property.

    Key features:
    - Checkbox in first column
    - Track multiple selections
    - on_selection_change callback
    - select_all() and clear_selection() methods
    """
    with html.div().classes("nc-component"):
        ui.label("SelectionTable - Checkbox Multi-Select").classes("text-h6 q-mb-md")
        ui.markdown("""
        **SelectionTable** adds a checkbox column for selecting multiple rows.
        
        ```python
        from ng_loba.crud import SelectionTable
        
        def on_selection_change(selected_ids):
            print(f"Selected: {selected_ids}")
        
        table = SelectionTable(
            state={},
            data_source=store,
            config=config,
            on_selection_change=on_selection_change,
        )
        await table.build()
        
        # Get selected IDs
        selected = table.selected_ids
        ```
        """)

        selection_label = ui.label("No items selected").classes("nc-text-muted")

        def handle_selection_change(selected_ids):
            count = len(selected_ids)
            selection_label.text = f"Selected {count} item(s): {selected_ids}" if count else "No items selected"

        # Create the SelectionTable using shared singleton store
        store = get_user_store()
        config = TableConfig(
            columns=get_user_columns(),
            empty_message="No users found",
        )

        table = SelectionTable(
            state={},
            data_source=store,
            config=config,
            on_selection_change=handle_selection_change,
        )
        await table.build()

        # Buttons to demonstrate selection methods
        with html.div().classes("nc-view-stack-toolbar"):
            with html.button().classes("nc-btn nc-btn-secondary").on("click", table.select_all):  # type: ignore
                html.span("Select All")
            with html.button().classes("nc-btn nc-btn-secondary").on("click", table.clear_selection):  # type: ignore
                html.span("Clear Selection")


# =============================================================================
# Section: Tabs Demo
# =============================================================================

async def build_tabs_demo():
    """
    Tabs Demo
    =========

    Tabs provides a simple tab-based navigation component. Each tab has a
    key, label, and async render function.

    Key features:
    - Simple tab bar with underline indicator
    - Async render functions for each tab
    - Automatic panel switching
    """
    with html.div().classes("nc-component"):
        ui.label("Tabs - Tab-Based Navigation").classes("text-h6 q-mb-md")
        ui.markdown("""
        **Tabs** provides simple tab navigation with async content rendering.
        
        ```python
        from ng_loba.crud import Tabs
        
        async def render_tab1():
            ui.label("Tab 1 content")
        
        async def render_tab2():
            ui.label("Tab 2 content")
        
        tabs = Tabs([
            ("tab1", "First Tab", render_tab1),
            ("tab2", "Second Tab", render_tab2),
        ])
        await tabs.build()
        ```
        """)

        # Tab content renderers using shared singleton stores
        async def render_products():
            config = TableConfig(columns=get_product_columns()[:3])
            table = ListTable(state={}, data_source=get_product_store(), config=config)
            await table.build()

        async def render_users():
            config = TableConfig(columns=get_user_columns()[:3])
            table = ListTable(state={}, data_source=get_user_store(), config=config)
            await table.build()

        async def render_settings():
            ui.label("Settings panel content would go here.")

        # Create the Tabs
        tabs = Tabs([
            ("products", "Products", render_products),
            ("users", "Users", render_users),
            ("settings", "Settings", render_settings),
        ])
        await tabs.build()


# =============================================================================
# Section: Dialog Demo
# =============================================================================

def build_dialog_demo():
    """
    Dialog Demo
    ===========

    Dialog is a positioned card overlay that provides modal functionality.
    It can be used for confirmations, forms, or any content that needs
    user focus.

    Key features:
    - Backdrop click to close
    - ESC key to close
    - actions() context for footer buttons
    - Large variant available
    """
    with html.div().classes("nc-component"):
        ui.label("Dialog - Modal Overlay").classes("text-h6 q-mb-md")
        ui.markdown("""
        **Dialog** provides modal overlay functionality with a semi-transparent backdrop.
        
        ```python
        from ng_loba.crud import Dialog
        
        with Dialog() as dlg:
            ui.label("Dialog content here")
            with dlg.actions():
                ui.button("OK", on_click=dlg.close)
        
        # Open the dialog
        dlg.open()
        ```
        """)

        # Dialog content
        with Dialog() as demo_dialog:
            ui.label("This is a dialog!").classes("text-h6")
            ui.label("Click the backdrop or press ESC to close.")
            with demo_dialog.actions():
                with html.button().classes("nc-btn nc-btn-primary").on("click", demo_dialog.close):  # type: ignore
                    html.span("Close Dialog")

        # Button to open dialog
        with html.button().classes("nc-btn nc-btn-primary").on("click", demo_dialog.open):  # type: ignore
            html.span("Open Dialog")


# =============================================================================
# Main Page
# =============================================================================

@ui.page("/")
async def main_page():
    """Main showcase page with all component demos."""
    page_init()  # Load nicecrud CSS and Bootstrap icons

    ui.add_head_html("""
    <style>
        body { background-color: #f5f7fa; }
        .showcase-container { max-width: 1000px; margin: 0 auto; padding: 24px; }
        .showcase-section { background: white; border-radius: 8px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); }
        .showcase-header { margin-bottom: 32px; text-align: center; }
        .showcase-header h1 { color: #303133; margin-bottom: 8px; }
        .showcase-header p { color: #909399; }
        pre { background: #f5f7fa; padding: 12px; border-radius: 4px; overflow-x: auto; }
        code { font-family: 'Fira Code', monospace; font-size: 13px; }
    </style>
    """)

    with ui.element("div").classes("showcase-container"):
        # Header
        with ui.element("div").classes("showcase-header"):
            ui.html("<h1>🎨 nicecrud Component Showcase</h1>")
            ui.html("<p>A comprehensive demo of all nicecrud components for NiceGUI</p>")

        # Introduction
        with ui.element("div").classes("showcase-section"):
            ui.label("Getting Started").classes("text-h5 q-mb-md")
            ui.markdown("""
            **nicecrud** is a CRUD component library for [NiceGUI](https://nicegui.io) applications.
            It provides clean, Element UI-inspired components for building data-driven interfaces.
            
            **Installation:**
            ```bash
            pip install ng_loba  # Will be renamed to nicecrud
            ```
            
            **Basic Setup:**
            ```python
            from nicegui import ui
            from ng_loba.crud import page_init, DataTable, Column, TableConfig
            
            @ui.page("/")
            async def main():
                page_init()  # Load CSS and icons
                
                # Your components here...
            
            ui.run()
            ```
            """)

        # DataTable Demo
        with ui.element("div").classes("showcase-section"):
            await build_datatable_demo()

        # ListTable Demo
        with ui.element("div").classes("showcase-section"):
            await build_listtable_demo()

        # ActionTable Demo
        with ui.element("div").classes("showcase-section"):
            await build_actiontable_demo()

        # SelectionTable Demo
        with ui.element("div").classes("showcase-section"):
            await build_selectiontable_demo()

        # Tabs Demo
        with ui.element("div").classes("showcase-section"):
            await build_tabs_demo()

        # Dialog Demo
        with ui.element("div").classes("showcase-section"):
            build_dialog_demo()

        # Component Summary
        with ui.element("div").classes("showcase-section"):
            ui.label("Component Summary").classes("text-h5 q-mb-md")
            ui.markdown("""
            | Component | Use Case |
            |-----------|----------|
            | **DataTable** | Editable table with modal add/edit dialogs |
            | **ListTable** | Read-only table with clickable rows (master-detail) |
            | **ActionTable** | Table with custom Edit/Delete action buttons |
            | **SelectionTable** | Multi-select table with checkboxes |
            | **Tabs** | Tab-based content navigation |
            | **Dialog** | Modal overlay for forms/confirmations |
            | **DetailCard** | Read-only detail view for selected item |
            | **EditCard** | Inline edit form (used with ViewStack) |
            | **ViewStack** | Master-detail-edit navigation coordinator |
            
            **CSS Design System:**
            - All components use `nc-*` CSS class prefix
            - Element UI / Bootstrap inspired styling
            - Native HTML elements where possible
            - CSS custom properties for easy theming
            """)


ui.run(title="nicecrud Showcase", port=8080)
