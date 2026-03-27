"""
Custom Table Example - Build your own table component using StoreComponent.

This example demonstrates:
- Inheriting from StoreComponent
- Implementing @ui.refreshable async def build()
- Custom row rendering with click handlers
- Using observer pattern for automatic refresh

Run from project root:
    python -m ng_rdm.examples.custom_table

Then open http://localhost:8080 in your browser.
"""

from nicegui import app, ui, html
from ng_rdm.components import ObservableRdmComponent, rdm_init
from ng_rdm.models import FieldSpec, Validator
from ng_rdm.store import DictStore


class HighlightTable(ObservableRdmComponent):
    """A custom table that highlights rows based on a condition.

    Shows how to build your own store-connected table component by:
    1. Inheriting from StoreComponent (provides data_source, observer, CRUD helpers)
    2. Implementing @ui.refreshable async def build()
    3. Adding custom behavior (highlighting, click handlers)
    """

    def __init__(
        self,
        state: dict,
        data_source,
        columns: list[tuple[str, str]],  # (field, label) pairs
        highlight_field: str,
        highlight_values: list,
        on_row_click=None,
    ):
        super().__init__(state, data_source)
        self.columns = columns
        self.highlight_field = highlight_field
        self.highlight_values = highlight_values
        self.on_row_click = on_row_click

    def _should_highlight(self, row: dict) -> bool:
        return row.get(self.highlight_field) in self.highlight_values

    @ui.refreshable_method
    async def build(self):
        await self.load_data()

        with html.div().classes("rdm-table-card rdm-component"):
            with html.table().classes("rdm-table"):
                with html.thead():
                    with html.tr():
                        for field, label in self.columns:
                            html.th(label)

                with html.tbody():
                    if not self.data:
                        with html.tr():
                            with html.td().props(f"colspan={len(self.columns)}"):
                                html.span("No data").classes("rdm-text-muted")
                    else:
                        for row in self.data:
                            self._build_row(row)

    def _build_row(self, row: dict):
        row_class = "rdm-clickable"
        if self._should_highlight(row):
            row_class += " rdm-selected"

        tr = html.tr().classes(row_class)
        if self.on_row_click:
            tr.on("click", lambda _, r=row: self.on_row_click(r))   # type: ignore

        with tr:
            for field, _label in self.columns:
                with html.td():
                    value = row.get(field, "")
                    html.span(str(value) if value else "")


TASKS = [
    {"id": 0, "title": "Write documentation", "priority": "high", "status": "pending"},
    {"id": 1, "title": "Fix bug #123", "priority": "high", "status": "in_progress"},
    {"id": 2, "title": "Review PR", "priority": "medium", "status": "pending"},
    {"id": 3, "title": "Deploy to staging", "priority": "low", "status": "done"},
    {"id": 4, "title": "Update dependencies", "priority": "medium", "status": "pending"},
]


@ui.page("/")
async def main():
    rdm_init()

    ui.label("Custom Table Component Example").classes("text-h4")
    ui.label("Shows how to build a store-connected table by inheriting from StoreComponent").classes("text-caption")

    store = DictStore(field_specs={
        "title": FieldSpec(validators=[
            Validator(message="Title required", validator=lambda v, _: bool(v and v.strip()))
        ])
    })
    store._items = [t.copy() for t in TASKS]

    state: dict = {"selected": None}
    selected_label = ui.label("Click a row to select").classes("rdm-text-muted")

    def on_select(row):
        state["selected"] = row
        selected_label.text = f"Selected: {row['title']} (priority: {row['priority']})"

    table = HighlightTable(
        state=state,
        data_source=store,
        columns=[
            ("title", "Task"),
            ("priority", "Priority"),
            ("status", "Status"),
        ],
        highlight_field="priority",
        highlight_values=["high"],
        on_row_click=on_select,
    )

    ui.separator()

    with ui.card().classes("w-full"):
        await table.build()

    ui.separator()
    ui.label("Actions (table auto-refreshes via observer):").classes("text-h6")

    async def add_task():
        await store.create_item({
            "title": f"New task #{len(store._items)}",
            "priority": "low",
            "status": "pending"
        })

    async def mark_all_done():
        for item in store._items[:]:
            await store.update_item(item["id"], {"status": "done"})

    with ui.row():
        ui.button("Add Task", on_click=add_task)
        ui.button("Mark All Done", on_click=mark_all_done)


app.on_startup(lambda: print("Open http://localhost:8080 in your browser"))
ui.run(title="Custom Table Example", port=8080)
