"""
Components without a Store - RdmDataSource from scratch.

Demonstrates that RDM components work with any object satisfying the
RdmDataSource protocol, without inheriting from Store or any base class.

Run:  python -m ng_rdm.examples.custom_datasource
Open: http://localhost:8080
"""
import asyncio
from pathlib import Path
from typing import Any, Callable

from nicegui import app, ui, Client

from ng_rdm.components import (
    rdm_init, Column, TableConfig, FormConfig,
    ActionButtonTable, EditDialog,
    Col,
)
from ng_rdm.store import StoreEvent


# =============================================================================
# Custom data source - implements RdmDataSource protocol without inheriting it
# =============================================================================

class ListDataSource:
    """Minimal RdmDataSource backed by a plain list.

    Copy this as a starting point for wrapping REST APIs, CSV files, etc.
    Note: never inherits from RdmDataSource — structural typing only.
    """

    def __init__(self, items: list[dict]):
        self._items = list(items)
        self._next_id = max((i["id"] for i in items), default=0) + 1
        self._observers: list[Callable] = []

    async def create_item(self, item: dict) -> dict | None:
        item = {**item, "id": self._next_id}
        self._next_id += 1
        self._items.append(item)
        await self._notify(StoreEvent(verb="create", item=item))
        return item

    async def read_items(
        self,
        filter_by: dict | None = None,
        q: Any = None,
        join_fields: list[str] = [],
        limit: int | None = None,
        offset: int = 0,
        order_by: list[str] | None = None,
    ) -> list[dict]:
        items = self._match(filter_by, q)
        if order_by:
            for key in reversed(order_by):  # right-to-left for a stable multi-key sort
                reverse = key.startswith("-")
                field = key[1:] if reverse else key
                items.sort(key=lambda it, f=field: (it.get(f) is None, it.get(f)), reverse=reverse)
        if offset:
            items = items[offset:]
        if limit is not None:
            items = items[:limit]
        return items

    async def read_counts(
        self,
        filter_by: dict | None = None,
        q: Any = None,
        group_by: str | None = None,
    ) -> int | dict:
        items = self._match(filter_by, q)
        if group_by is None:
            return len(items)
        counts: dict = {}
        for it in items:
            counts[it.get(group_by)] = counts.get(it.get(group_by), 0) + 1
        return counts

    async def update_item(self, id: int, partial_item: dict) -> dict | None:
        for item in self._items:
            if item["id"] == id:
                item.update(partial_item)
                await self._notify(StoreEvent(verb="update", item=dict(item)))
                return dict(item)
        return None

    async def delete_item(self, item: dict) -> None:
        self._items = [i for i in self._items if i["id"] != item["id"]]
        await self._notify(StoreEvent(verb="delete", item=item))

    def _match(self, filter_by: dict | None, q: Any = None) -> list[dict]:
        """Apply the equality filter and the predicate — this source speaks callables."""
        items = list(self._items)
        if filter_by:
            items = [i for i in items if all(i.get(k) == v for k, v in filter_by.items())]
        return [i for i in items if q(i)] if q else items

    # Predicate building — required for TableConfig(show_search=True). The table never
    # builds a predicate itself, so each data source stays free to use its own dialect.
    def search_q(self, text: str, fields: list[str]) -> Callable[[dict], bool] | None:
        if not text or not fields:
            return None
        needle = text.lower()
        return lambda item: any(needle in str(item.get(f) or "").lower() for f in fields)

    def and_q(self, a: Any, b: Any) -> Any:
        if a is None or b is None:
            return b if a is None else a
        return lambda item: a(item) and b(item)

    def validate(self, item: dict) -> tuple[bool, dict]:
        if not item.get("title", "").strip():
            return (False, {"col_name": "title", "error_msg": "required", "error_value": ""})
        return (True, {})

    def add_observer(self, observer: Callable, topics: dict | None = None) -> None:
        self._observers.append(observer)

    def remove_observer(self, observer: Callable) -> None:
        self._observers = [o for o in self._observers if o is not observer]

    async def _notify(self, event: StoreEvent) -> None:
        await asyncio.gather(*[obs(event) for obs in list(self._observers)])


# =============================================================================
# Page
# =============================================================================

datasource = ListDataSource([
    {"id": 1, "title": "Plan the sprint", "done": True},
    {"id": 2, "title": "Write tests", "done": False},
    {"id": 3, "title": "Deploy to production", "done": False},
])

task_columns = [
    Column(name="title", label="Task", width_percent=65),
    Column(name="done", label="Done", width_percent=20,
           formatter=lambda x: "✓" if x else ""),
]

form_config = FormConfig(
    columns=[
        Column(name="title", label="Task", required=True),
        Column(name="done", label="Done", ui_type=ui.checkbox),
    ],
    title_add="New Task",
    title_edit="Edit Task",
)

table_config = TableConfig(
    columns=task_columns,
    add_button="+ Add Task",
    empty_message="No tasks",
)


@ui.page("/")
async def main(client: Client):
    rdm_init(extra_css=Path(__file__).parent / "examples.css")
    await client.connected()

    app.storage.user.setdefault("ui_state", {"table": {}, "dialog": {}})
    ui_state = app.storage.user["ui_state"]

    with Col(style="width: 100%; max-width: 42rem; margin: 0 auto; padding: 1rem"):
        ui.label("RDM Components — Custom Data Source").classes("demo-section-heading")
        ui.markdown(
            "The `ListDataSource` class below satisfies the `RdmDataSource` protocol "
            "without inheriting from any RDM base class — structural typing only. "
            "It could wrap a REST API, a CSV file, or any other backend."
        )

        dialog = EditDialog(
            state=ui_state["dialog"],
            data_source=datasource,
            config=form_config,
        )

        async def on_delete(row: dict):
            await datasource.delete_item(row)

        table = ActionButtonTable(
            state=ui_state["table"],
            data_source=datasource,
            config=table_config,
            on_add=dialog.open_for_new,
            on_edit=dialog.open_for_edit,
            on_delete=on_delete,
        )
        await table.render()


ui.run(title="Custom DataSource — ng_rdm", storage_secret="custom_ds_1928")
