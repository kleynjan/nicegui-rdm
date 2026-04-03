"""
ListTable - Read-only table with clickable rows for navigation.

Uses native HTML <table> elements for clean, semantic markup.
Integrates with store for automatic refresh on data changes.
"""
from typing import Any, Awaitable, Callable, Union

from nicegui import html, ui

from ..base import ObservableRdmTable, TableConfig
from ..protocol import RdmDataSource


class ListTable(ObservableRdmTable):
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
        data_source: RdmDataSource,
        config: TableConfig,
        state: dict | None = None,
        *,
        filter_by: dict[str, Any] | None = None,
        on_click: Callable[[int | None], Union[Awaitable[None], None]] | None = None,
        on_add: Callable[[], Awaitable[None] | None] | None = None,
        transform: Callable[[list[dict]], list[dict]] | None = None,
        row_key: str = "id",
        join_fields: list[str] | None = None,
        render_toolbar: Callable[[], None] | None = None,
        auto_observe: bool = True,
    ):
        super().__init__(
            data_source=data_source, config=config, state=state,
            filter_by=filter_by, transform=transform,
            join_fields=join_fields, on_add=on_add,
            render_toolbar=render_toolbar, auto_observe=auto_observe,
        )
        self.on_click = on_click
        self.row_key = row_key

    def _render_cell(self, col, value, row: dict):
        """Render a single cell value. Overrides base to add ui.badge support."""
        if col.ui_type == ui.badge:
            color_map = col.parms.get("color_map", {})
            color = color_map.get(str(value), "grey")
            if value:
                ui.badge(str(value)).props(f"color={color}")
        else:
            super()._render_cell(col, value, row)

    @ui.refreshable_method
    async def build(self):
        """Build the table using native HTML elements."""
        await self.load_data()
        self._build_toolbar("top")

        if not self.data:
            if self.config.empty_message:
                with html.div().classes("rdm-empty"):
                    html.span(self.config.empty_message).classes("rdm-empty-text")
            self._build_toolbar("bottom")
            return

        with html.div().classes("rdm-table-card rdm-component show-refresh"):
            with html.table().classes("rdm-table"):
                # Header
                with html.thead():
                    with html.tr():
                        for col in self.config.columns:
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
                            for col in self.config.columns:
                                with html.td():
                                    self._render_cell(col, item.get(col.name, ""), item)

        self._build_toolbar("bottom")
