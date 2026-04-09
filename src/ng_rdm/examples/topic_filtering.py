"""
Topic Filtering — selective store event routing.

Run:  python -m ng_rdm.examples.topic_filtering
Open: http://localhost:8080  |  debug: http://localhost:8080/rdm-debug
"""
from pathlib import Path

from nicegui import app, ui, Client

from ng_rdm import DictStore, store_registry
from ng_rdm.store import StoreEvent
from ng_rdm.components import (
    rdm_init, Column, TableConfig, FormConfig,
    ActionButtonTable, EditDialog,
    Row, Col, Separator,
)

# =============================================================================
# Store setup
# =============================================================================

customer_store = DictStore()
customer_store.set_topic_fields(["country"])
store_registry.register_store("demo", "customers", customer_store)

SEED_DATA = [
    {"id": 1, "name": "Alice Johnson", "country": "USA"},
    {"id": 2, "name": "Bob Smith", "country": "USA"},
    {"id": 3, "name": "Charlie Brown", "country": "USA"},
    {"id": 4, "name": "Diana Windsor", "country": "UK"},
    {"id": 5, "name": "Edward Thames", "country": "UK"},
]


async def seed_store():
    if not await customer_store.read_items():
        for item in SEED_DATA:
            await customer_store.create_item(item)


# =============================================================================
# Column / config definitions
# =============================================================================

customer_table_config = TableConfig(
    columns=[
        Column(name="name", label="Name", width_percent=55),
        Column(name="country", label="Country", width_percent=30),
    ],
    show_add_button=False,
    show_delete_button=False,
    empty_message="No customers",
)

customer_form_config = FormConfig(
    columns=[Column(name="name", label="Name", required=True)],
    title_edit="Edit Customer",
)


# =============================================================================
# Page
# =============================================================================

@ui.page("/")
async def index(client: Client):

    rdm_init(extra_css=Path(__file__).parent / "examples.css", show_refresh_transitions=True, show_store_event_log=True)
    await seed_store()
    await client.connected()

    app.storage.user.setdefault("ui_state", {
        "left_table": {}, "right_table": {}, "dialog": {}, "selection": {},
    })
    ui_state = app.storage.user["ui_state"]

    with Col(gap="1rem", style="width: 100%; max-width: 64rem; margin: 0 auto; padding: 1rem"):

        # ── section 1: topic-filtered side-by-side tables ────────────────────

        ui.label("Topic Filtering").classes("demo-section-heading")
        ui.markdown(
            "1. Each table initially subscribes to a single country topic. "
            "Editing a UK customer on the right fires a country=UK event — "
            "only the UK table refreshes, the USA table stays silent."
            "\n"
            "2. Set the right table to 'All' and then modify a USA customer - "
            "now both tables receive the event and refresh."
        )

        # Shared EditDialog: one instance handles both tables
        edit_dialog = EditDialog(
            state=ui_state["dialog"],
            data_source=customer_store,
            config=customer_form_config,
        )

        with Row(gap="2rem", style="width: 100%"):
            for side, default_country in [("Left", "USA"), ("Right", "UK")]:
                state_key = f"{side.lower()}_table"
                with Col(style="flex: 1"):
                    ui.label(f"{side} Table").style("font-size: 1rem; font-weight: 600")

                    table = ActionButtonTable(
                        state=ui_state[state_key],
                        data_source=customer_store,
                        config=customer_table_config,
                        filter_by={"country": default_country},
                        auto_observe=False,
                        on_edit=edit_dialog.open_for_edit,
                    )
                    table.observe(topics={"country": default_country})
                    await table.build()

                    # Radio filter — changes both filter_by and topic subscription
                    ui.label("Filter:").classes("demo-caption")

                    async def on_filter_change(e, t=table):
                        value = e.value
                        if value == "All":
                            t.filter_by = None
                            t.reobserve(topics=None)
                        else:
                            t.filter_by = {"country": value}
                            t.reobserve(topics={"country": value})
                        await t.build.refresh()

                    ui.radio(["USA", "UK", "All"], value=default_country,
                             on_change=on_filter_change).props("inline")

        # # ── section 2: UI state preservation ─────────────────────────────────

        # Separator()
        # ui.label("UI State Preservation").classes("demo-section-heading")
        # ui.markdown(
        #     "Select customers below, then edit a name in the tables above. "
        #     "The table refreshes (store notification fires) but your selection "
        #     "persists — because `state[\"selected_ids\"]` lives in "
        #     "`app.storage.user`, outside the component."
        # )

        # selection_config = TableConfig(
        #     columns=[
        #         Column(name="name", label="Name", width_percent=50),
        #         Column(name="country", label="Country", width_percent=35),
        #     ],
        #     show_add_button=False,
        #     show_edit_button=False,
        #     show_delete_button=False,
        # )

        # sel_table = SelectionTable(
        #     state=ui_state["selection"],
        #     data_source=customer_store,
        #     config=selection_config,
        # )
        # await sel_table.build()

        # selection_label = ui.label("").classes("demo-caption")
        # selection_label.bind_text_from(
        #     ui_state["selection"], "selected_ids",
        #     backward=lambda ids: (
        #         f"Selected: {len(ids)} customer(s) — IDs {sorted(ids)}"
        #         if ids else "No selection"
        #     ),
        # )

        # with Row():
        #     Button("Select All", on_click=sel_table.select_all)  # type: ignore[arg-type]
        #     Button("Clear", color="secondary", on_click=sel_table.clear_selection)  # type: ignore[arg-type]

        # ── section 3: event log ──────────────────────────────────────────────

        Separator()
        ui.label("Event Log").classes("demo-section-heading")
        ui.markdown(
            "A plain observer (no topic filter) records every store event. "
            "Compare with the filtered tables above — they only receive events "
            "matching their subscribed country."
        )

        log = ui.log(max_lines=30).style("width: 100%; height: 160px; font-size: 0.85rem;")

        async def on_event(event: StoreEvent):
            country = event.item.get("country", "?")
            name = event.item.get("name", "?")
            log.push(f"[{event.verb.upper()}] {name!r}  country={country!r}")

        customer_store.add_observer(on_event)

        async def cleanup():
            customer_store.remove_observer(on_event)

        client.on_disconnect(cleanup)

        # ── footer ────────────────────────────────────────────────────────────

        Separator()
        ui.link("Open Debug Panel → (tip: open side by side)",
                target="/rdm-debug", new_tab=True).classes("demo-caption")

ui.run(title="Topic Filtering — ng_rdm", storage_secret="topic_filter_1928")
