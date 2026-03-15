"""
NavigateTable - read-only div-based table with click-to-navigate rows.
Uses div-based flexbox layout with crudy-* classes, same as direct.py and explicit.py.
Supports Column.ui_type for custom cell rendering (e.g., ui.badge).
"""
from typing import Any, Callable

from nicegui import ui

from .base import Column, TableConfig
from ._table_base import BaseCrudTable
from .protocol import CrudDataSource


def _render_cell(col: Column, value):
    """Render a single cell based on Column.ui_type and formatter."""
    if col.ui_type == ui.badge:
        color_map = col.parms.get("color_map", {})
        color = color_map.get(str(value), "grey")
        if value:
            ui.badge(str(value)).props(f"color={color}")
    else:
        display = col.formatter(value) if col.formatter else (str(value) if value else "")
        ui.label(display)


class NavigateTable(BaseCrudTable):
    """Read-only table with clickable rows for navigation.

    Uses div-based flexbox layout (same pattern as DirectEditTable/ExplicitEditTable).
    Integrates with store for automatic refresh on data changes.
    """

    def __init__(
        self,
        state: dict,
        data_source: CrudDataSource,
        config: TableConfig,
        filter_by: dict[str, Any] | None = None,
        on_click: Callable | None = None,
        transform: Callable[[list[dict]], list[dict]] | None = None,
        row_key: str = "id",
        join_fields: list[str] | None = None,
    ):
        super().__init__(state, data_source, config)
        self.filter_by = filter_by
        self.on_click = on_click
        self.transform = transform
        self.row_key = row_key
        self._extra_join_fields = join_fields or []

    async def load_data(self, join_fields: list[str] | None = None):
        all_joins = list(set(self.config.join_fields + self._extra_join_fields))
        self.data = await self.data_source.read_items(
            filter_by=self.filter_by,
            join_fields=join_fields or all_joins,
        )
        if self.transform:
            self.data = self.transform(self.data)

    @ui.refreshable
    async def build(self):
        await self.load_data()

        if not self.data:
            if self.config.empty_message:
                ui.label(self.config.empty_message).classes("empty-state")
            return

        with ui.card().classes("crudy-navigate"):
            with ui.row().classes("crudy-header"):
                for col in self.config.table_columns:
                    ui.label(col.label or col.name).style(col.width_style).classes(f"{col.name}")

            for item in self.data:
                key = item.get(self.row_key)
                row = ui.row().classes("crudy-row crudy-row-navigate")
                if self.on_click:
                    row.on("click", lambda _, k=key: self.on_click(k))  # type: ignore
                with row:
                    for col in self.config.table_columns:
                        with ui.element("div").style(col.width_style):
                            if col.render:
                                col.render(item)
                            else:
                                _render_cell(col, item.get(col.name, ""))
