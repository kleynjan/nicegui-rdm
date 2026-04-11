"""
Chips Example — custom cell rendering with Column.render.

Shows how to plug an arbitrary NiceGUI render function into a table column.
The Status column emits colored HTML chips via a custom renderer; the other
columns render plain text as usual. A button mutates the store out-of-band
and the table auto-refreshes.

Run:  python -m ng_rdm.examples.chips
Open: http://localhost:8080
"""
from nicegui import Client, app, ui

from ng_rdm import DictStore, store_registry
from ng_rdm.components import Column, Row, SelectionTable, TableConfig, rdm_init


# =============================================================================
# Chip CSS — passed as a string to rdm_init(extra_css=...)
# =============================================================================

CHIP_CSS = """
.status-chip {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    color: #fff;
    text-transform: capitalize;
    margin: 1px 2px;
}
.status-chip-active   { background: #16a34a; }
.status-chip-invited  { background: #2563eb; }
.status-chip-pending  { background: #d97706; }
.status-chip-expired  { background: #6b7280; }
"""


# =============================================================================
# Store + seed data
# =============================================================================

store = DictStore()
store_registry.register_store("people", store)

SEED = [
    {"name": "Alice Banner", "role": "Admin", "statuses": ["active", "invited"]},
    {"name": "Bob Carter", "role": "Editor", "statuses": ["pending"]},
    {"name": "Carol Donovan", "role": "Viewer", "statuses": ["expired"]},
]


@app.on_startup
async def startup():
    if not await store.read_items():
        for item in SEED:
            await store.create_item(item)


# =============================================================================
# Custom cell renderer — the integration point for Column.render
# =============================================================================

def render_statuses(row: dict) -> None:
    """Render each status value as a colored chip inside the table cell.

    This function is passed as Column(render=render_statuses).  It is called by
    ObservableRdmComponent._render_cell() inside the <td> context, so any
    NiceGUI element created here lands directly in that cell.
    """
    statuses = row.get("statuses") or []
    chips = " ".join(
        f'<span class="status-chip status-chip-{s}">{s}</span>'
        for s in statuses
    )
    ui.html(chips, sanitize=False)


# =============================================================================
# Table config — render= wires the custom function to the Status column
# =============================================================================

config = TableConfig(
    columns=[
        Column(name="name", label="Name", width_percent=30),
        Column(name="role", label="Role", width_percent=20),
        # Custom renderer: pass a callable that receives the full row dict
        Column(name="statuses", label="Status", width_percent=50, render=render_statuses),
    ],
    empty_message="No people",
)


# =============================================================================
# Page
# =============================================================================

@ui.page("/")
async def main(client: Client):
    rdm_init(extra_css=CHIP_CSS)
    await client.connected()

    ui.label("Column.render — custom chip cells").style("font-size: 1.75rem; font-weight: 700")
    ui.label(
        "The Status column uses Column(render=...) to call a custom function that "
        "emits HTML chips. Click the button below to toggle Bob's 'active' status "
        "and watch the table refresh via a store event."
    ).style("margin-bottom: 1.25rem; max-width: 42rem")

    table = SelectionTable(
        data_source=store,
        config=config,
        show_checkboxes=False,
        multi_select=False,
    )
    await table.build()

    async def toggle_bob_active():
        rows = await store.read_items(filter_by={"name": "Bob Carter"})
        if not rows:
            return
        bob = rows[0]
        statuses: list[str] = list(bob.get("statuses") or [])
        if "active" in statuses:
            statuses.remove("active")
        else:
            statuses.append("active")
        await store.update_item(bob["id"], {"statuses": statuses})

    with Row(style="margin-top: 1rem"):
        ui.button("Toggle Bob's 'active' status", on_click=toggle_bob_active)


ui.run(title="Chips — ng_rdm", storage_secret="chips_1928")
