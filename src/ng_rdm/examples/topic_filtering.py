"""
Topic Filtering Example - demonstrates selective event subscriptions.

Run: python -m ng_rdm.examples.topic_filtering
Then open http://localhost:8080 to see two DataTables with topic-based filtering.
Open http://localhost:8080/rdm-debug to see the event stream.

Key concepts demonstrated:
- set_topic_fields() to enable topic routing on a field
- reobserve(topics) to dynamically change what events a table receives
- Editing UK data on one table doesn't refresh the USA table (and vice versa)
"""

from nicegui import html, ui

from ng_rdm import DictStore, store_registry
from ng_rdm.components import rdm_init, DataTable, Column, TableConfig, FormConfig

# Create store and configure topic filtering on 'country' field
customer_store = DictStore()
customer_store.set_topic_fields(["country"])
store_registry.register_store("demo", "customers", customer_store)

# Seed data: 3 USA customers, 2 UK customers
SEED_DATA = [
    {"id": 1, "name": "Alice Johnson", "country": "USA"},
    {"id": 2, "name": "Bob Smith", "country": "USA"},
    {"id": 3, "name": "Charlie Brown", "country": "USA"},
    {"id": 4, "name": "Diana Windsor", "country": "UK"},
    {"id": 5, "name": "Edward Thames", "country": "UK"},
]

# Column configuration
customer_columns = [
    Column(name="id", label="ID", width_percent=15, editable=False),
    Column(name="name", label="Name", width_percent=50, editable=True),
    Column(name="country", label="Country", width_percent=35, editable=False),
]

customer_config = TableConfig(
    columns=customer_columns,
    show_add_button=False,
    show_edit_button=True,
    show_delete_button=False,
)

customer_form_config = FormConfig(
    columns=[Column(name="name", label="Name", editable=True, required=True)],
)


async def seed_store():
    """Populate the store with initial data if empty."""
    existing = await customer_store.read_items()
    if not existing:
        for item in SEED_DATA:
            await customer_store.create_item(item)


@ui.page("/")
async def index():
    rdm_init()
    await seed_store()

    ui.label("Topic Filtering Demo").classes("text-2xl font-bold mb-2")
    ui.label(
        "Edit a customer's name. If left table filters UK and right filters USA, "
        "editing a UK customer won't refresh the USA table."
    ).classes("text-gray-600 mb-4")

    # State for filter selections
    left_filter = {"value": "USA"}
    right_filter = {"value": "UK"}

    # Create two tables side by side
    with ui.row().classes("w-full gap-8"):
        # Left table
        with ui.column().classes("flex-1"):
            ui.label("Left Table").classes("font-semibold text-lg mb-2")

            left_table = DataTable(
                state={},
                data_source=customer_store,
                config=customer_config,
                form_config=customer_form_config,
                filter_by={"country": left_filter["value"]},
                auto_observe=False,
            )
            left_table.observe(topics={"country": left_filter["value"]})
            await left_table.build()

            # Radio buttons for left table
            with html.div().classes("mt-4"):
                ui.label("Filter:").classes("text-sm text-gray-500 mb-1")

                async def on_left_change(e):
                    value = e.value
                    left_filter["value"] = value
                    if value == "All":
                        left_table.filter_by = None
                        left_table.reobserve(topics=None)
                    else:
                        left_table.filter_by = {"country": value}
                        left_table.reobserve(topics={"country": value})
                    await left_table.build.refresh()

                ui.radio(
                    ["USA", "UK", "All"],
                    value=left_filter["value"],
                    on_change=on_left_change,
                ).props("inline")

        # Right table
        with ui.column().classes("flex-1"):
            ui.label("Right Table").classes("font-semibold text-lg mb-2")

            right_table = DataTable(
                state={},
                data_source=customer_store,
                config=customer_config,
                form_config=customer_form_config,
                filter_by={"country": right_filter["value"]},
                auto_observe=False,
            )
            right_table.observe(topics={"country": right_filter["value"]})
            await right_table.build()

            # Radio buttons for right table
            with html.div().classes("mt-4"):
                ui.label("Filter:").classes("text-sm text-gray-500 mb-1")

                async def on_right_change(e):
                    value = e.value
                    right_filter["value"] = value
                    if value == "All":
                        right_table.filter_by = None
                        right_table.reobserve(topics=None)
                    else:
                        right_table.filter_by = {"country": value}
                        right_table.reobserve(topics={"country": value})
                    await right_table.build.refresh()

                ui.radio(
                    ["USA", "UK", "All"],
                    value=right_filter["value"],
                    on_change=on_right_change,
                ).props("inline")

    # Debug page link
    with html.div().classes("mt-8 pt-4 border-t"):
        ui.link(text="Open Debug Panel", target="/rdm-debug",
                new_tab=True).classes("text-sm text-blue-600 hover:underline")
        ui.label(
            "Watch the event stream to see which observers get notified"
        ).classes("text-sm text-gray-500 ml-4")


ui.run(title="Topic Filtering Demo", port=8080)
