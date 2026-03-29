"""
SelectionTable - Table with checkbox selection column for multi-select.

Uses native HTML <table> elements for clean, semantic markup.
Tracks selected row IDs via the selected_ids property.
"""
from typing import Any, Callable

from nicegui import html, ui

from .base import ObservableRdmTable, TableConfig
from .protocol import RdmDataSource


class SelectionTable(ObservableRdmTable):
    """Table with checkbox selection in first column.

    Uses native HTML table elements with rdm-* CSS classes.
    Tracks selected row IDs via the selected_ids property.

    Args:
        state: Shared state dict
        data_source: RdmDataSource (typically a Store)
        config: TableConfig with column definitions
        filter_by: Optional filter dict for data loading
        transform: Optional transform function for loaded data
        row_key: Field to use as row identifier (default "id")
        join_fields: Additional join fields for data loading
        on_selection_change: Callback when selection changes, receives set of selected IDs
    """

    def __init__(
        self,
        state: dict,
        data_source: RdmDataSource,
        config: TableConfig,
        filter_by: dict[str, Any] | None = None,
        transform: Callable[[list[dict]], list[dict]] | None = None,
        row_key: str = "id",
        join_fields: list[str] | None = None,
        on_selection_change: Callable[[set[int]], None] | None = None,
        auto_observe: bool = True,
    ):
        super().__init__(
            state, data_source, config,
            filter_by=filter_by, transform=transform,
            join_fields=join_fields, auto_observe=auto_observe,
        )
        self.row_key = row_key
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

    def _on_checkbox_change(self, row_key: int, checked: bool):
        """Handle checkbox state change."""
        if checked:
            self._selected_ids.add(row_key)
        else:
            self._selected_ids.discard(row_key)
        if self.on_selection_change:
            self.on_selection_change(self._selected_ids)

    @ui.refreshable_method
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
                        # Checkbox column header (narrow)
                        html.th("").style("width: 48px;")
                        for col in self.config.columns:
                            th = html.th(col.label or col.name)
                            if col.width_percent:
                                th.style(f"width: {col.width_percent}%")

                # Body
                with html.tbody():
                    for item in self.data:
                        key = item.get(self.row_key)
                        if key is None:
                            continue
                        is_checked = key in self._selected_ids

                        with html.tr().classes("rdm-selected" if is_checked else ""):
                            # Checkbox cell
                            with html.td().style("width: 48px;"):
                                ui.checkbox(
                                    value=is_checked,
                                    on_change=lambda e, k=key: self._on_checkbox_change(k, e.value)
                                )

                            # Data cells
                            for col in self.config.columns:
                                with html.td():
                                    self._render_cell(col, item.get(col.name, ""), item)
