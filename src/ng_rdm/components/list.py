"""
ListTable - Read-only table with clickable rows for navigation.

Uses native HTML <table> elements for clean, semantic markup.
Integrates with store for automatic refresh on data changes.
"""
from typing import Any, Callable

from nicegui import html, ui

from .base import ObservableRdmComponent, TableConfig
from .protocol import RdmDataSource


class ListTable(ObservableRdmComponent):
    """Read-only table with clickable rows for navigation.

    Uses native HTML table elements with rdm-* CSS classes.
    Integrates with store for automatic refresh on data changes.

    Args:
        state: Shared state dict
        data_source: RdmDataSource (typically a Store)
        config: TableConfig with column definitions
        filter_by: Optional filter dict for data loading
        on_click: Callback when row is clicked, receives row key (id)
        transform: Optional transform function for loaded data
        row_key: Field to use as row identifier (default "id")
        join_fields: Additional join fields for data loading
    """

    def __init__(
        self,
        state: dict,
        data_source: RdmDataSource,
        config: TableConfig,
        filter_by: dict[str, Any] | None = None,
        on_click: Callable[[int | None], None] | None = None,
        transform: Callable[[list[dict]], list[dict]] | None = None,
        row_key: str = "id",
        join_fields: list[str] | None = None,
        auto_observe: bool = True,
    ):
        super().__init__(state, data_source)
        self.config = config
        self.filter_by = filter_by
        self.on_click = on_click
        self.transform = transform
        self.row_key = row_key
        self._extra_join_fields = join_fields or []
        if auto_observe:
            self.observe(topics=filter_by)

    async def load_data(self, join_fields: list[str] | None = None):
        """Load data from store with filter and join fields."""
        all_joins = list(set(self.config.join_fields + self._extra_join_fields))
        await super().load_data(
            join_fields=join_fields or all_joins,
            filter_by=self.filter_by,
            transform=self.transform,
        )

    def _render_cell(self, col, value, row: dict):
        """Render a single cell value. Overrides base to add ui.badge support."""
        if col.ui_type == ui.badge:
            color_map = col.parms.get("color_map", {})
            color = color_map.get(str(value), "grey")
            if value:
                ui.badge(str(value)).props(f"color={color}")
        else:
            super()._render_cell(col, value, row)

    @ui.refreshable
    async def build(self):
        """Build the table using native HTML elements."""
        await self.load_data()

        if not self.data:
            if self.config.empty_message:
                with html.div().classes("rdm-empty"):
                    html.span(self.config.empty_message).classes("rdm-empty-text")
            return

        with html.div().classes("rdm-table-card rdm-component"):
            with html.table().classes("rdm-table"):
                # Header
                with html.thead():
                    with html.tr():
                        for col in self.config.table_columns:
                            th = html.th(col.label or col.name)
                            if col.width_percent:
                                th.style(f"width: {col.width_percent}%")

                # Body
                with html.tbody():
                    for item in self.data:
                        key = item.get(self.row_key)
                        tr = html.tr().classes("rdm-clickable")
                        if self.on_click:
                            tr.on("click", lambda _, k=key: self.on_click(k))  # type: ignore

                        with tr:
                            for col in self.config.table_columns:
                                with html.td():
                                    self._render_cell(col, item.get(col.name, ""), item)
