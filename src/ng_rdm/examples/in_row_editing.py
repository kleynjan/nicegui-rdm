"""
Direct Edit Example — inline editable DirectEditTable.

Demonstrates a custom ObservableRdmTable subclass where every cell is an
editable widget. Text/number cells save on blur; checkbox cells save on
change. The toolbar "+ Add task" button toggles a blank new-item row with
save/cancel icons. The trash icon deletes immediately (no confirmation).

Below the table, a ui.input + button pair mutates the same store
out-of-band — the DirectEditTable auto-refreshes via store events.

Run:  python -m ng_rdm.examples.direct_edit
Open: http://localhost:8080
Creates: in_row.sqlite3
"""
from pathlib import Path
from typing import Any, Awaitable, Callable, cast

from nicegui import Client, app, html, ui
from tortoise import fields

from ng_rdm import store_registry
from ng_rdm.components import (
    Button,
    Col,
    Column,
    ObservableRdmTable,
    RdmDataSource,
    Row,
    RowAction,
    Separator,
    TableConfig,
    rdm_init,
)
from ng_rdm.components.fields import build_cell_field
from ng_rdm.models import FieldSpec, RdmModel, Validator
from ng_rdm.store import TortoiseStore, init_db

# =============================================================================
# DirectEditTable — inline editable table subclass
# =============================================================================

class DirectEditTable(ObservableRdmTable):
    """Table where every cell renders as an editable widget.

    - Text/number cells save on blur (partial update, only the changed field).
    - Checkbox cells save on value-change.
    - Toolbar Add button toggles a blank "new item" row with save/cancel icons.
    - Delete icon removes the row immediately (no confirmation).
    """

    def __init__(
        self,
        data_source: RdmDataSource,
        config: TableConfig,
        state: dict | None = None,
        *,
        filter_by: dict[str, Any] | None = None,
        on_add: Callable[[], Awaitable[None] | None] | None = None,
        render_toolbar: Callable[[], None] | None = None,
        auto_observe: bool = True,
    ):
        super().__init__(
            data_source=data_source, config=config, state=state,
            filter_by=filter_by,
            on_add=on_add or self._toggle_new_item,
            render_toolbar=render_toolbar, auto_observe=auto_observe,
        )
        self.state.setdefault("show_new_item", False)
        self.state.setdefault("new_item", self._blank_item())

    def _blank_item(self) -> dict[str, Any]:
        return {c.name: c.default_value for c in self.config.columns}

    def _reset_new_item(self) -> None:
        self.state["new_item"].clear()
        self.state["new_item"].update(self._blank_item())

    @ui.refreshable_method
    async def build(self):
        await self.load_data()
        self._build_toolbar("top")

        with html.div().classes("rdm-table-card rdm-component show-refresh"):
            with html.table().classes("rdm-table rdm-direct-table"):
                with html.thead():
                    with html.tr():
                        for col in self.config.columns:
                            th = html.th(col.label or col.name)
                            if col.width_percent:
                                th.style(f"width: {col.width_percent}%")
                        if self.config.show_delete_button:
                            html.th("").classes("rdm-col-actions")

                with html.tbody():
                    if not self.data and not self.state["show_new_item"]:
                        with html.tr():
                            colspan = len(self.config.columns) + (1 if self.config.show_delete_button else 0)
                            with html.td().props(f"colspan={colspan}"):
                                html.span(self.config.empty_message or "No data").classes("rdm-text-muted")
                    else:
                        for item in self.data:
                            self._build_data_row(item)
                        if self.state["show_new_item"]:
                            self._build_new_row()

        self._build_toolbar("bottom")

    def _build_data_row(self, item: dict[str, Any]) -> None:
        async def delete(r: dict) -> None:
            await self._delete(r, confirm=False)

        with html.tr():
            for col in self.config.columns:
                with html.td().classes("rdm-direct-cell"):
                    self._build_editable_cell(col, item, save=True)
            if self.config.show_delete_button:
                with html.td().classes("rdm-col-actions"):
                    RowAction(icon="trash", tooltip="Delete", color="default", callback=delete).render(item)

    def _build_new_row(self) -> None:
        with html.tr().classes("rdm-direct-new-row"):
            for col in self.config.columns:
                with html.td().classes("rdm-direct-cell"):
                    self._build_editable_cell(col, self.state["new_item"], save=False)
            if self.config.show_delete_button:
                with html.td().classes("rdm-col-actions"):
                    with html.div().classes("rdm-actions"):
                        RowAction(
                            icon="check-square", tooltip="Save", color="primary",
                            callback=lambda _r: self._handle_add(),
                        ).render({})
                        RowAction(
                            icon="x-square", tooltip="Cancel", color="default",
                            callback=lambda _r: self._cancel_new_item(),
                        ).render({})

    def _build_editable_cell(self, col: Column, item: dict[str, Any], save: bool) -> None:
        """Render an editable cell bound to item[col.name].

        save=True attaches the auto-save handler (blur or value-change); save=False
        leaves the widget unattached (new-item row, committed via the save icon).
        """
        if col.editable is False or col.ui_type is None:
            self._render_cell(col, item.get(col.name, ""), item)
            return
        el = build_cell_field(col, item)
        if el is None or not save:
            return
        if col.ui_type is ui.checkbox:
            cast(ui.checkbox, el).on_value_change(lambda _e, c=col.name, i=item: self._handle_save(c, i))
        else:
            el.on("blur", lambda _e, c=col.name, i=item: self._handle_save(c, i))

    async def _handle_save(self, col_name: str, item: dict[str, Any]) -> None:
        if item.get("id") is None:
            return
        partial = {col_name: item[col_name]}
        (valid, _err) = self._validate(partial)
        if valid:
            await self._update(item["id"], partial)

    async def _handle_add(self) -> None:
        created = await self._validate_and_create(dict(self.state["new_item"]))
        if created:
            self._reset_new_item()
            self.state["show_new_item"] = False
            # Store event triggers auto-refresh; new-row disappears on next build.

    def _cancel_new_item(self) -> None:
        self._reset_new_item()
        self.state["show_new_item"] = False
        self.build.refresh()

    def _toggle_new_item(self) -> None:
        self.state["show_new_item"] = not self.state["show_new_item"]
        if self.state["show_new_item"]:
            self._reset_new_item()
        self.build.refresh()


# =============================================================================
# Model
# =============================================================================

class Task(RdmModel):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=100)
    priority = fields.IntField(default=3)
    done = fields.BooleanField(default=False)

    field_specs = {
        "title": FieldSpec(validators=[
            Validator(message="Title is required", validator=lambda v, _: bool(v and str(v).strip())),
        ]),
        "priority": FieldSpec(validators=[
            Validator(message="Priority must be 1..5", validator=lambda v, _: v is None or 1 <= int(v) <= 5),
        ]),
    }

    class Meta(RdmModel.Meta):
        table = "direct_task"


# =============================================================================
# Database
# =============================================================================

DB_PATH = Path(__file__).parent / "in_row.sqlite3"
init_db(app, f"sqlite://{DB_PATH}", modules={"models": [__name__]}, generate_schemas=True)


async def seed_data():
    if await Task.all().count() > 0:
        return
    for title, priority, done in [
        ("Draft release notes", 2, False),
        ("Review PR #42", 1, False),
        ("Update dependencies", 3, True),
        ("Plan sprint retro", 4, False),
    ]:
        await Task.create(title=title, priority=priority, done=done)


@app.on_startup
async def startup():
    await seed_data()
    store_registry.register_store("task", TortoiseStore(Task))


# =============================================================================
# Column / config
# =============================================================================

task_cols = [
    Column(name="title", label="Title", ui_type=ui.input, width_percent=55, required=True),
    Column(name="priority", label="Priority", ui_type=ui.number, default_value=3,
           width_percent=20, parms={"min": 1, "max": 5}),
    Column(name="done", label="Done", ui_type=ui.checkbox, default_value=False, width_percent=15),
]


# =============================================================================
# Page
# =============================================================================

@ui.page("/")
async def main(client: Client):
    rdm_init(extra_css=Path(__file__).parent / "examples.css", show_refresh_transitions=True)
    await client.connected()

    store = store_registry.get_store("task")

    with Col(classes="demo-content-column"):
        ui.label("Custom table subclass: in-row editing").style("font-size: 2rem")
        ui.label(
            "Every cell is an editable widget. Edit a title or priority and tab "
            "away to save; toggle a checkbox to save immediately. Click "
            "'+ Add task' to open an inline new-item row. The trash icon deletes."
        ).style("margin-bottom: 1.5rem")

        table = DirectEditTable(
            data_source=store,
            config=TableConfig(columns=task_cols, add_button="+ Add task"),
        )
        await table.build()

        # Separator(style="margin: 1.5rem 0")

        # ui.label("Out-of-band store mutations").style("font-size: 1.25rem; font-weight: 600")
        # ui.label(
        #     "The controls below mutate the store directly. DirectEditTable "
        #     "subscribes to the same store and re-renders automatically."
        # ).style("margin-bottom: 0.5rem")

        # with Row(align="flex-end", gap="0.75rem"):
        #     quick = ui.input(label="Quick task title").style("min-width: 20rem")

        #     async def add_task():
        #         title = (quick.value or "").strip()
        #         if not title:
        #             return
        #         await store.create_item({"title": title, "priority": 3, "done": False})
        #         quick.set_value("")

        #     Button("Add via store", on_click=add_task)

        #     async def toggle_first():
        #         items = await store.read_items()
        #         if not items:
        #             return
        #         first = items[0]
        #         await store.update_item(first["id"], {"done": not first["done"]})

        #     Button("Toggle first task done", color="secondary", on_click=toggle_first)


ui.run(title="In-row Editing — ng_rdm", storage_secret="in_row_edit_1928")
