"""
demo_app.py — minimal standalone app used by make_demo_gif.py.

Shows a custom reactive table (ObservableRdmComponent) watching a DictStore.
Browser A edits; Browser B watches live updates.

Run:  conda run -n rdm_test python scripts/demo_app.py
Open: http://localhost:7788
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nicegui import app, ui, html
from ng_rdm.components import rdm_init, Button, Row, Col, ObservableRdmComponent
from ng_rdm.store import DictStore

DEMO_STORE = DictStore()

class TaskTable(ObservableRdmComponent):
    """Reactive table that highlights high-priority tasks."""

    def __init__(self, data_source):
        super().__init__(data_source=data_source)
        self.observe()

    @ui.refreshable_method
    async def build(self):
        await self.load_data()
        with html.div().classes("rdm-component show-refresh rdm-table-card"):
            with html.table().classes("rdm-table"):
                with html.thead():
                    with html.tr():
                        html.th("Task")
                        html.th("Priority")
                with html.tbody():
                    if not self.data:
                        with html.tr():
                            html.td("No tasks yet").props('colspan=2')
                    for row in self.data:
                        is_high = row.get("priority") == "high"
                        css = "rdm-selected" if is_high else ""
                        with html.tr().classes(css):
                            html.td(row.get("title", ""))
                            html.td(row.get("priority", "normal"))


@app.on_startup
async def startup():
    await DEMO_STORE.create_item({"title": "Fix bug #42", "priority": "normal"})
    await DEMO_STORE.create_item({"title": "Write tests", "priority": "normal"})
    await DEMO_STORE.create_item({"title": "Deploy release", "priority": "high"})
    await DEMO_STORE.create_item({"title": "Update docs", "priority": "normal"})


@ui.page("/")
async def index():
    rdm_init(show_refresh_transitions=True)

    with Col(style="max-width: 520px; margin: 2rem auto; padding: 0 1rem;"):
        ui.label("ng_rdm — Reactive Data Management").style(
            "font-size: 1.5rem; font-weight: 600; margin-bottom: 0.25rem;"
        )
        ui.label(
            "Both browsers share the same store. Edit in one — the other updates instantly."
        ).style("color: #666; margin-bottom: 1.5rem; font-size: 0.95rem;")

        table = TaskTable(data_source=DEMO_STORE)
        await table.build()

        ui.label("Add a task:").style("margin-top: 1.25rem; font-weight: 500;")
        with Row(align="flex-end", style="flex-wrap: wrap; gap: 0.5rem;"):
            title_input = ui.input("Task title").style("flex: 1; min-width: 160px;")
            priority_select = ui.select(
                ["high", "normal"], label="Priority", value="normal"
            ).style("width: 110px;")

            async def add_task():
                if title_input.value.strip():
                    await DEMO_STORE.create_item({
                        "title": title_input.value.strip(),
                        "priority": priority_select.value,
                    })
                    title_input.set_value("")

            Button("Add Task", on_click=add_task)

        async def toggle_task_2():
            items = await DEMO_STORE.read_items()
            if len(items) >= 2:
                item = items[1]
                new_prio = "high" if item["priority"] == "normal" else "normal"
                await DEMO_STORE.update_item(item["id"], {"priority": new_prio})

        with Row(style="margin-top: 0.5rem;"):
            Button(
                "Toggle priority of 'Write tests'",
                color="secondary",
                on_click=toggle_task_2,
            )


ui.run(port=7788, title="ng_rdm Demo", storage_secret="demo_gif_42", reload=False)
