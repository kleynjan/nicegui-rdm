"""
ActionButtonTable - Read-only table with action buttons on every row.

Actions are handled via callbacks (edit/delete), not inline editing.
Extends BaseCrudTable for automatic store subscription.
"""

from typing import Any, Awaitable, Callable

from nicegui import ui

from ._table_base import BaseCrudTable
from .base import TableConfig
from .protocol import CrudDataSource


class ActionButtonTable(BaseCrudTable):
    """Read-only table with action buttons (Edit/Delete) on every row.

    Unlike ExplicitEditTable, this table:
    - Shows buttons on ALL rows (not just selected)
    - Uses text buttons instead of icons
    - Delegates edit/delete actions to callbacks (typically opening dialogs)
    - Provides automatic refresh via store subscription

    Args:
        state: Dictionary for table state
        data_source: CrudDataSource (typically a Store)
        config: TableConfig with column definitions
        filter_by: Optional filter dict for data loading
        on_edit: Callback when Edit button clicked, receives row dict
        on_delete: Callback when Delete button clicked, receives row dict
        edit_label: Label for edit button (default "Edit")
        delete_label: Label for delete button (default "Delete")
    """

    def __init__(
        self,
        state: dict,
        data_source: CrudDataSource,
        config: TableConfig,
        filter_by: dict[str, Any] | None = None,
        on_edit: Callable[[dict], Awaitable[None]] | None = None,
        on_delete: Callable[[dict], Awaitable[None]] | None = None,
        edit_label: str = "Edit",
        delete_label: str = "Delete",
    ):
        super().__init__(state, data_source, config)
        self.filter_by = filter_by
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.edit_label = edit_label
        self.delete_label = delete_label

    async def load_data(self):
        """Load data from store with filter and join fields from config."""
        self.data = await self.data_source.read_items(
            filter_by=self.filter_by,
            join_fields=self.config.join_fields,
        )

    def _build_header(self):
        """Build header row using divs with flexbox pattern"""
        with ui.row().classes("crudy-header"):
            for column in self.config.columns:
                ui.label(column.label or column.name).classes(f"crudy-col-{column.name}").style(column.width_style)
            # Actions column
            ui.label("").classes("crudy-col-actions")

    @ui.refreshable
    async def build(self):
        """Build the table UI"""
        await self.load_data()
        with ui.card().classes("crudy-card crudy-action-table"):
            self._build_header()
            self._build_body()

    def _build_body(self):
        """Build table body with action buttons on every row"""
        if not self.data:
            with ui.row().classes("crudy-row"):
                ui.label(self.config.empty_message or "No data").classes("text-muted")
            return

        for row in self.data:
            self._build_row(row)

    def _build_row(self, row: dict):
        """Build a single row with display columns and action buttons"""
        with ui.row().classes("crudy-row"):
            # Data columns
            for col in self.config.columns:
                col_name = col.name
                with ui.element("div").classes(f"crudy-col-{col_name}").style(col.width_style):
                    if col.render:
                        col.render(row)
                    elif col.on_click:
                        raw_value = row.get(col_name, "") or ""
                        display = col.formatter(raw_value) if col.formatter else str(raw_value)
                        handler = col.on_click
                        ui.label(display).classes("crudy-link").on(
                            "click", lambda _, r=row, h=handler: h(r)
                        )
                    else:
                        raw_value = row.get(col_name, "") or ""
                        display = col.formatter(raw_value) if col.formatter else str(raw_value)
                        ui.label(display)

            # Action buttons - always visible
            with ui.element("div").classes("crudy-col-actions crudy-action-buttons"):
                if self.on_edit and self.config.show_edit_button:
                    edit_fn = self.on_edit
                    ui.button(self.edit_label, on_click=lambda _, r=row: edit_fn(r)) \
                        .props('size=xs').classes("btn-action btn-edit")
                if self.on_delete and self.config.show_delete_button:
                    delete_fn = self.on_delete
                    ui.button(self.delete_label, on_click=lambda _, r=row: delete_fn(r)) \
                        .props("size=xs").classes("btn-action btn-delete")
