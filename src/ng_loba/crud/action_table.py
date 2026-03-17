"""
ActionTable - Read-only table with action buttons on every row.

Uses native HTML <table> elements for clean, semantic markup.
Actions are handled via callbacks (edit/delete), not inline editing.
"""
from typing import Any, Awaitable, Callable

from nicegui import html, ui

from ._table_base import BaseCrudTable
from .base import TableConfig
from .protocol import CrudDataSource


class ActionTable(BaseCrudTable):
    """Read-only table with action buttons (Edit/Delete) on every row.

    Uses native HTML table elements with nc-* CSS classes.
    Delegates edit/delete actions to callbacks (typically opening dialogs).

    Args:
        state: Shared state dict
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

    def _render_cell(self, col, value, row: dict):
        """Render a single cell value."""
        if col.render:
            col.render(row)
        elif col.on_click:
            raw_value = row.get(col.name, "") or ""
            display = col.formatter(raw_value) if col.formatter else str(raw_value)
            handler = col.on_click
            html.span(display).classes("nc-link").on(
                "click", lambda _, r=row, h=handler: h(r)
            )
        else:
            raw_value = row.get(col.name, "") or ""
            display = col.formatter(raw_value) if col.formatter else str(raw_value)
            html.span(display)

    @ui.refreshable
    async def build(self):
        """Build the table using native HTML elements."""
        await self.load_data()

        with html.div().classes("nc-table-card nc-component"):
            with html.table().classes("nc-table"):
                # Header
                with html.thead():
                    with html.tr():
                        for col in self.config.columns:
                            th = html.th(col.label or col.name)
                            if col.width_percent:
                                th.style(f"width: {col.width_percent}%")
                        # Actions column header
                        html.th("").classes("nc-col-actions")

                # Body
                with html.tbody():
                    if not self.data:
                        with html.tr():
                            colspan = len(self.config.columns) + 1
                            with html.td().props(f"colspan={colspan}"):
                                html.span(
                                    self.config.empty_message or "No data"
                                ).classes("nc-text-muted")
                    else:
                        for row in self.data:
                            self._build_row(row)

    def _build_row(self, row: dict):
        """Build a single data row with action buttons."""
        with html.tr():
            # Data columns
            for col in self.config.columns:
                with html.td():
                    self._render_cell(col, row.get(col.name, ""), row)

            # Action buttons column
            with html.td().classes("nc-col-actions"):
                with html.div().classes("nc-actions"):
                    if self.on_edit and self.config.show_edit_button:
                        edit_fn = self.on_edit
                        with html.button().classes("nc-btn nc-btn-primary nc-btn-sm").on(
                            "click", lambda _, r=row: edit_fn(r)
                        ):
                            html.span(self.edit_label)

                    if self.on_delete and self.config.show_delete_button:
                        delete_fn = self.on_delete
                        with html.button().classes("nc-btn nc-btn-secondary nc-btn-sm").on(
                            "click", lambda _, r=row: delete_fn(r)
                        ):
                            html.span(self.delete_label)


# Backwards compatibility alias
ActionButtonTable = ActionTable
