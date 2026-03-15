"""
CheckboxTable - read-only table with checkbox selection column.
Uses div-based flexbox layout with crudy-* classes.
Exposes selected_ids property for retrieving checked rows.
"""
from typing import Any, Callable

from nicegui import ui

from .base import Column, TableConfig
from ._table_base import BaseCrudTable
from .protocol import CrudDataSource


class CheckboxTable(BaseCrudTable):
    """Table with checkbox selection in first column.

    Uses div-based flexbox layout (same pattern as NavigateTable).
    Tracks selected row IDs via the selected_ids property.
    """

    def __init__(
        self,
        state: dict,
        data_source: CrudDataSource,
        config: TableConfig,
        filter_by: dict[str, Any] | None = None,
        transform: Callable[[list[dict]], list[dict]] | None = None,
        row_key: str = "id",
        join_fields: list[str] | None = None,
        on_selection_change: Callable[[set[int]], None] | None = None,
    ):
        super().__init__(state, data_source, config)
        self.filter_by = filter_by
        self.transform = transform
        self.row_key = row_key
        self._extra_join_fields = join_fields or []
        self.on_selection_change = on_selection_change
        self._selected_ids: set[int] = set()

    @property
    def selected_ids(self) -> set[int]:
        """Get currently selected row IDs."""
        return self._selected_ids.copy()

    def clear_selection(self):
        """Clear all selections."""
        self._selected_ids.clear()
        if self.on_selection_change:
            self.on_selection_change(self._selected_ids)

    def select_all(self):
        """Select all rows."""
        for item in self.data:
            key = item.get(self.row_key)
            if key is not None:
                self._selected_ids.add(key)
        if self.on_selection_change:
            self.on_selection_change(self._selected_ids)

    async def load_data(self, join_fields: list[str] | None = None):
        all_joins = list(set(self.config.join_fields + self._extra_join_fields))
        self.data = await self.data_source.read_items(
            filter_by=self.filter_by,
            join_fields=join_fields or all_joins,
        )
        if self.transform:
            self.data = self.transform(self.data)

    def _on_checkbox_change(self, row_key: int, checked: bool):
        """Handle checkbox state change."""
        if checked:
            self._selected_ids.add(row_key)
        else:
            self._selected_ids.discard(row_key)
        if self.on_selection_change:
            self.on_selection_change(self._selected_ids)

    @ui.refreshable
    async def build(self):
        await self.load_data()

        if not self.data:
            if self.config.empty_message:
                ui.label(self.config.empty_message).classes("empty-state")
            return

        with ui.card().classes("crudy-checkbox"):
            # Header row
            with ui.row().classes("crudy-header"):
                # Checkbox column header (narrow)
                ui.label("").style("width: 40px; flex-shrink: 0;")
                for col in self.config.table_columns:
                    ui.label(col.label or col.name).style(col.width_style)

            # Data rows
            for item in self.data:
                key = item.get(self.row_key)
                if key is None:
                    continue
                is_checked = key in self._selected_ids

                with ui.row().classes("crudy-row crudy-row-checkbox"):
                    # Checkbox cell
                    with ui.element("div").style("width: 40px; flex-shrink: 0;"):
                        ui.checkbox(
                            value=is_checked,
                            on_change=lambda e, k=key: self._on_checkbox_change(k, e.value)
                        )

                    # Data cells
                    for col in self.config.table_columns:
                        with ui.element("div").style(col.width_style):
                            if col.render:
                                col.render(item)
                            else:
                                value = item.get(col.name, "")
                                display = col.formatter(value) if col.formatter else str(value) if value else ""
                                ui.label(display)
