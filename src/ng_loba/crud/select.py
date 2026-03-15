"""
SelectTable - read-only table with single-row selection using Quasar ui.table.
"""
from typing import Any, Callable

from nicegui import ui

from .base import TableConfig
from ._table_base import BaseCrudTable
from ..store.base import StoreEvent


class SelectTable(BaseCrudTable):
    """Read-only table with click-to-select/deselect single row.

    Uses Quasar ui.table for built-in sorting and styling.
    Integrates with store for automatic refresh on data changes.
    """

    def __init__(
        self,
        state: dict,
        data_source: Any,
        config: TableConfig,
        state_key: str = "selected_key",
        on_selection: Callable[[int | None], None] | None = None,
        body_slot_string: str = "",
    ):
        super().__init__(state, data_source, config)
        self.state_key = state_key
        self.on_selection = on_selection
        self.body_slot_string = body_slot_string
        self._table: ui.table | None = None

        if self.state_key not in self.state:
            self.state[self.state_key] = None

    @property
    def selected_key(self) -> int | None:
        return self.state.get(self.state_key)

    @selected_key.setter
    def selected_key(self, value: int | None):
        self.state[self.state_key] = value

    def _refresh_selection(self) -> None:
        """Update table's visual selection to match state."""
        if self._table is None:
            return
        self._table.selected.clear()
        if self.selected_key is not None:
            selected_rows = [row for row in self._table.rows if row["id"] == self.selected_key]
            if selected_rows:
                self._table.selected.append(selected_rows[0])

    def _on_cell_click(self, new_key: int | None) -> None:
        new_key = None if new_key == self.selected_key else new_key
        self.selected_key = new_key
        self._refresh_selection()
        if self.on_selection:
            self.on_selection(new_key)

    def _build_columns(self) -> list[dict]:
        """Convert TableConfig columns to Quasar column spec."""
        columns = []
        for col in self.config.table_columns:
            q_col = {
                "name": col.name,
                "label": col.label or col.name,
                "field": col.name,
                "align": "left",
                "sortable": True,
            }
            columns.append(q_col)
        return columns

    async def _handle_datasource_change(self, event: StoreEvent):
        """Handle store changes - clear selection if deleted item was selected."""
        if event.verb == "delete" and event.item.get("id") == self.selected_key:
            self.selected_key = None
            if self.on_selection:
                self.on_selection(None)
        await self.build.refresh()  # type: ignore

    @ui.refreshable
    async def build(self):
        """Build the select table UI."""
        await self.load_data()

        if not self.data:
            if self.config.empty_message:
                ui.label(self.config.empty_message).classes("empty-state")
            return

        columns = self._build_columns()

        self._table = ui.table(
            columns=columns,
            rows=self.data,
            row_key="id",
        ).classes("crudy-select-table")

        # Custom body-cell slot for click handling and optional conditional styling
        self._table.add_slot(
            "body-cell",
            r"""
            <q-td :props="props" """ + self.body_slot_string + r""" @click="$parent.$emit('cell_click', props)">
                {{ props.value }}
            </q-td>
            """,
        )
        self._table.on("cell_click", lambda msg: self._on_cell_click(msg.args["key"]))
        self._refresh_selection()
