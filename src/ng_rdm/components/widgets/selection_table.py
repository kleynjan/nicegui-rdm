"""
SelectionTable - Table with checkbox selection column for multi-select.

Uses native HTML <table> elements for clean, semantic markup.
Tracks selected row IDs via the selected_ids property.
"""
from typing import Any, Awaitable, Callable

from nicegui import html, ui

from ..base import ObservableRdmTable, TableConfig, Column
from ..i18n import _
from ..protocol import RdmDataSource


class SelectionTable(ObservableRdmTable):
    """Table with checkbox selection in first column.

    Uses native HTML table elements with rdm-* CSS classes.
    Tracks selected row IDs via the selected_ids property.

    Args:
        data_source: RdmDataSource (typically a Store)
        config: TableConfig with column definitions
        state: Shared state dict
        show_checkboxes: Whether to show checkboxes in the first column
        multi_select: Whether to allow multiple selection
        filter_by: Optional filter dict for data loading
        q: Optional non-equality predicate (Tortoise Q; callable on DictStore) — for search
        transform: Optional transform function for loaded data
        row_key: Field to use as row identifier (default "id")
        join_fields: Additional join fields for data loading
        on_selection_change: Callback when selection changes, receives set of selected IDs
        on_add: Callback for the toolbar Add button (the button renders only when set)
        limit: Optional hard cap on rows (for bounded query-views over large entities)
        order_by: Optional initial DB-side ordering, e.g. ["name", "-created_at"]
    """

    def __init__(
        self,
        data_source: RdmDataSource,
        config: TableConfig,
        state: dict | None = None,
        show_checkboxes: bool | None = None,
        multi_select: bool | None = None,
        *,
        filter_by: dict[str, Any] | None = None,
        q: Any | None = None,
        transform: Callable[[list[dict]], list[dict]] | None = None,
        row_key: str = "id",
        join_fields: list[str] | None = None,
        on_selection_change: Callable[[set[int]], None] | None = None,
        on_add: Callable[[], Awaitable[None] | None] | None = None,
        render_toolbar: Callable[[], Any] | None = None,   # sync or async; awaited if awaitable
        auto_observe: bool = True,
        limit: int | None = None,
        order_by: list[str] | None = None,
        clear_selection_on_page_change: bool = False,
    ):
        super().__init__(
            data_source=data_source, config=config, state=state,
            filter_by=filter_by, q=q, transform=transform,
            join_fields=join_fields, on_add=on_add,
            render_toolbar=render_toolbar, auto_observe=auto_observe,
            limit=limit, order_by=order_by,
        )
        self.row_key = row_key
        self.on_selection_change = on_selection_change
        self._clear_on_page_change = clear_selection_on_page_change
        self._last_offset = self.state.get('offset', 0)
        self.state.setdefault('selected_ids', [])
        self.state.setdefault('show_checkboxes', show_checkboxes if show_checkboxes is not None else True)
        self.state.setdefault('multi_select', multi_select if multi_select is not None else True)

    async def _publish_page_state(self, read: dict) -> None:
        """Publish the selection alongside the page numbers.

        Selection is keyed on row_key, not position, so it survives a page change — which
        means a bulk action can operate on rows the user cannot see. `selected_offscreen`
        makes that visible (the built-in pager label surfaces it); pass
        clear_selection_on_page_change=True for page-scoped selection instead.
        """
        if self._clear_on_page_change and read["offset"] != self._last_offset:
            self.state['selected_ids'] = []
        self._last_offset = read["offset"]
        selected = set(self.state['selected_ids'])
        self.state['selected_count'] = len(selected)
        self.state['selected_offscreen'] = len(selected - {i.get(self.row_key) for i in self.data})
        await super()._publish_page_state(read)

    def _default_page_label(self, first: int, last: int, total: int) -> str:
        label = super()._default_page_label(first, last, total)
        if count := self.state.get('selected_count', 0):
            label += f" · {count} {_('selected')}"
            if offscreen := self.state.get('selected_offscreen', 0):
                label += f" ({offscreen} {_('off page')})"
        return label

    def handle_row_click(self, row_key: int):
        self.toggle(row_key)

    def sync_state(self):
        """Sync state changes to UI. Called after selection changes."""
        self.build.refresh()
        if self.on_selection_change:
            self.on_selection_change(set(self.state['selected_ids']))

    @property
    def selected_ids(self) -> list[int]:
        """Get currently selected row IDs."""
        return self.state['selected_ids']

    def add_to_selection(self, row_key: int):
        """Add a specific row to selection (and immediately refresh)."""
        sset = set(self.state['selected_ids'])
        if not self.state['multi_select']:
            sset.clear()
        sset.add(row_key)
        self.state['selected_ids'] = list(sset) if sset else [row_key]

    def remove_from_selection(self, row_key: int):
        """Remove a specific row from selection (and immediately refresh)."""
        if row_key in self.state['selected_ids']:
            self.state['selected_ids'].remove(row_key)

    def toggle(self, row_key: int):
        """Select a specific row by key (and immediately refresh)."""
        if row_key not in self.state['selected_ids']:
            self.add_to_selection(row_key)
        else:
            self.remove_from_selection(row_key)
        self.sync_state()

    def clear_selection(self):
        """Clear all selections."""
        self.state['selected_ids'] = []
        self.sync_state()

    def select_all(self):
        """Select all rows."""
        for item in self.data:
            key = item.get(self.row_key)
            if key:
                self.add_to_selection(key)
        self.sync_state()

    @ui.refreshable_method
    async def build(self):  # type: ignore[override]  # refreshable_method descriptor vs base stub — see ObservableRdmComponent build contract
        """Build the table using native HTML elements."""
        await self.load_data()

        with html.div().classes("rdm-table-card rdm-component"):
            with html.table().classes("rdm-table"):
                # Header
                with html.thead():
                    with html.tr():
                        if self.state['show_checkboxes']:
                            # Checkbox column header (narrow)
                            html.th("").style("width: 48px;")
                        self._render_column_headers()

                # Body
                with html.tbody():
                    if not self.data:
                        self._render_empty_row(len(self.config.columns) + bool(self.state['show_checkboxes']))
                    for item in self.data:
                        key = item.get(self.row_key)
                        if key is None:
                            continue
                        is_checked = key in self.state['selected_ids']

                        with html.tr().classes("rdm-selected" if is_checked else ""):
                            if self.state['show_checkboxes']:
                                # Checkbox cell
                                with html.td().style("width: 48px;"):
                                    ui.checkbox(
                                        value=is_checked,
                                        on_change=lambda e, k=key: self.handle_row_click(k)
                                    ).mark(f"rdm-checkbox-{key}")

                            # Data cells
                            for col in self.config.columns:
                                with html.td().on("click", lambda _, k=key: self.handle_row_click(k)):
                                    self._render_cell(col, item.get(col.name, ""), item)
