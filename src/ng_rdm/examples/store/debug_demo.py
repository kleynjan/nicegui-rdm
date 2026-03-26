"""
Demo of the RDM Debug Page.

Run: python -m ng_rdm.examples.store.debug_demo
Then open http://localhost:8080/rdm-debug to see the event stream.
"""

from nicegui import ui

from ng_rdm import DictStore, enable_debug_page, store_registry
from ng_rdm.components import rdm_init, DataTable, Column, TableConfig

# Create store and register it
user_store = DictStore()
store_registry.register_store("demo", "users", user_store)

# Enable the debug page - this wires up event logging
enable_debug_page()

# Configure columns for the user table
user_columns = [
    Column(name="id", label="ID", width_percent=20),
    Column(name="name", label="Name", width_percent=80, editable=True),
]

user_config = TableConfig(
    table_columns=user_columns,
    dialog_columns=user_columns,
    show_add_button=True,
    show_edit_button=True,
    show_delete_button=True,
)


@ui.page("/")
async def index():
    rdm_init()

    ui.label("RDM Debug Demo").classes("text-2xl font-bold mb-4")

    with ui.row().classes("gap-4 mb-4"):
        ui.link("Open Debug Panel →", "/rdm-debug").classes("text-blue-500 underline")

    ui.label("User Table:").classes("font-semibold mb-2")

    table = DataTable(state={}, data_source=user_store, config=user_config)
    table.render_add_button()
    await table.build()

    ui.label(
        "Add/edit/delete users above, then check the debug panel to see events."
    ).classes("text-gray-500 text-sm mt-4")


ui.run(title="RDM Debug Demo", port=8080)
