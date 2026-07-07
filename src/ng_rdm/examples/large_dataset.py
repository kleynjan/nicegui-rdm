"""
Large-dataset Example — bounded views for entities too big to render whole.

Demonstrates the three reactive-view archetypes ng_rdm supports at scale. The store
is a CRUD-by-id gateway; a "view" is a separate, explicitly-bounded projection that
re-reads on a throttled cadence.

1. Query-view (users) — a capped, ordered, filterable table. auto_observe=False:
   it does NOT react to every store event (there are too many rows to re-render).
   It shows "N of M" using read_counts() and refines via a team filter + hard limit.

2. Count-view (bulk progress) — ReactiveCounts reads *counts* (not rows) grouped by
   status on a throttled cadence, and surfaces them via NiceGUI bind_text_from. No
   table is rebuilt; only the numbers change.

3. Scoped-live-view (one user's messages) — a ListTable filtered down to a handful of
   rows, auto_observe=True with topic filtering. A full re-read on throttle is cheap.

A background "sender" advances message statuses several times per second. The message
store uses throttle_ms=500, so the count header updates on a steady ~2 Hz cadence
(not per-event, not starved) even under the sustained update stream.

Run:  python -m ng_rdm.examples.large_dataset
Open: http://localhost:8080
Creates: large_dataset.sqlite3
"""
import asyncio
from pathlib import Path

from nicegui import Client, app, ui
from tortoise import fields

from ng_rdm import store_registry
from ng_rdm.components import (
    Col,
    Column,
    ListTable,
    ReactiveCounts,
    Row,
    Separator,
    TableConfig,
    rdm_init,
)
from ng_rdm.models import FieldSpec, RdmModel, Validator
from ng_rdm.store import TortoiseStore, init_db

# =============================================================================
# Models
# =============================================================================

TEAMS = ["Sales", "Support", "Engineering", "Ops"]
MSG_STATUSES = ["queued", "sent", "delivered", "failed"]
STATUS_COLORS = {"queued": "grey", "sent": "blue", "delivered": "green", "failed": "red"}


class AppUser(RdmModel):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    team = fields.CharField(max_length=40)
    status = fields.CharField(max_length=20, default="active")

    field_specs = {
        "name": FieldSpec(validators=[
            Validator(message="Name is required", validator=lambda v, _: bool(v and v.strip()))
        ])
    }

    class Meta(RdmModel.Meta):
        table = "ld_user"


class Message(RdmModel):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.AppUser", related_name="messages")
    status = fields.CharField(max_length=20, default="queued")

    class Meta(RdmModel.Meta):
        table = "ld_message"


# =============================================================================
# Database + seeding
# =============================================================================

DB_PATH = Path(__file__).parent / "large_dataset.sqlite3"
init_db(app, f"sqlite://{DB_PATH}", modules={"models": [__name__]}, generate_schemas=True)

N_USERS = 1500        # too many to render in one table — hence the query-view
BATCH_SIZE = 150      # the "bulk send" — the count-view tracks its progress
FANOUT_USERS = 24     # messages spread across the first N users (focus user gets several)


async def seed_data():
    if await AppUser.all().count() == 0:
        await AppUser.bulk_create([
            AppUser(name=f"User {i:04d}", team=TEAMS[i % len(TEAMS)],
                    status="active" if i % 7 else "inactive")
            for i in range(N_USERS)
        ])
    user_ids = [u["id"] for u in await AppUser.all().order_by("id").limit(FANOUT_USERS).values("id")]

    # Re-arm the message batch on every startup so the demo always starts fresh
    await Message.all().delete()
    await Message.bulk_create([
        Message(user_id=user_ids[i % FANOUT_USERS], status="queued")
        for i in range(BATCH_SIZE)
    ])
    return user_ids[0]  # focus user for the scoped-live view


async def run_sender():
    """Advance message statuses several times/sec; re-arm when the batch completes."""
    store = store_registry.get_store("messages")
    while True:
        rows = await Message.filter(status__in=["queued", "sent"]).limit(6).values("id", "status")
        if not rows:
            await asyncio.sleep(1.5)
            await Message.all().update(status="queued")  # loop the demo
            continue
        for r in rows:
            nxt = "sent" if r["status"] == "queued" else "delivered"
            await store.update_item(r["id"], {"status": nxt})
        await asyncio.sleep(0.15)


@app.on_startup
async def startup():
    focus_user_id = await seed_data()
    app.storage.general["focus_user_id"] = focus_user_id
    store_registry.register_store("users", TortoiseStore(AppUser))
    # Busy bulk view: bump the throttle so the count header updates ~2 Hz, not per-event.
    store_registry.register_store("messages", TortoiseStore(Message, throttle_ms=500))
    asyncio.create_task(run_sender())


# =============================================================================
# Column configs
# =============================================================================

user_cols = [
    Column(name="name", label="Name", width_percent=45),
    Column(name="team", label="Team", width_percent=35),
    Column(name="status", label="Status", width_percent=20),
]

message_cols = [
    Column(name="id", label="Message #", width_percent=50),
    Column(name="status", label="Status", ui_type=ui.badge,
           parms={"color_map": STATUS_COLORS}, width_percent=50),
]


# =============================================================================
# Page
# =============================================================================

@ui.page("/")
async def main(client: Client):
    rdm_init(extra_css=Path(__file__).parent / "examples.css")
    await client.connected()

    users_store = store_registry.get_store("users")
    message_store = store_registry.get_store("messages")
    focus_user_id = app.storage.general.get("focus_user_id", 1)

    with Col(classes="demo-content-column"):
        ui.label("Large-dataset patterns").classes("demo-section-heading")
        ui.label(
            "One store, three bounded views. Every reactive view stays small so its "
            "throttled re-read is cheap."
        ).classes("demo-subtitle")

        # ── 1. Query-view: capped, ordered, filterable users table ───────────
        Separator()
        ui.label("1 · Query-view — 1500 users, capped at 50").classes("demo-section-heading")

        users_table = ListTable(
            data_source=users_store,
            config=TableConfig(columns=user_cols, empty_message="No users"),
            order_by=["name"],
            limit=50,
            auto_observe=False,  # far too many rows to re-render on every store event
        )

        count_label = ui.label().classes("demo-subtitle")
        team_select = ui.select(["All", *TEAMS], value="All", label="Team")

        async def refine():
            team = team_select.value
            users_table.filter_by = None if team == "All" else {"team": team}
            await users_table.build.refresh()
            total = await users_store.read_counts(filter_by=users_table.filter_by)
            count_label.text = f"Showing {len(users_table.data)} of {total} users"

        team_select.on_value_change(refine)
        await users_table.build()
        await refine()  # initial "N of M" label

        # ── 2. Count-view: bulk-send progress via ReactiveCounts + binding ────
        Separator()
        ui.label("2 · Count-view — bulk send progress (updates ~2×/sec)").classes("demo-section-heading")

        counts = ReactiveCounts(message_store, group_by="status", keys=MSG_STATUSES)
        await counts.start()

        with Row(gap="1.5rem"):
            for status in MSG_STATUSES:
                with Col(gap="0.1rem"):
                    ui.label().bind_text_from(
                        counts.values, status, backward=lambda v: str(v or 0)
                    ).style("font-size: 1.8rem; font-weight: 700")
                    ui.label(status).classes("demo-subtitle")

        # ── 3. Scoped-live-view: one user's messages, reactive + throttled ────
        Separator()
        ui.label(f"3 · Scoped-live-view — messages for user #{focus_user_id}").classes("demo-section-heading")

        messages_table = ListTable(
            data_source=message_store,
            config=TableConfig(columns=message_cols, empty_message="No messages"),
            filter_by={"user_id": focus_user_id},  # topic-filtered: only this user's events wake it
            order_by=["id"],
            auto_observe=True,  # a handful of rows — a full re-read on throttle is cheap
        )
        await messages_table.build()


ui.run(title="Large dataset — ng_rdm", storage_secret="large_dataset_1928")
