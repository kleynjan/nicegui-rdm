"""
ActionButtonTable - Table with action buttons per row.

Uses native HTML <table> elements for clean, semantic markup.
Action rendering delegated to RowAction.render().
"""
from typing import Any, Awaitable, Callable

from nicegui import html, ui

from ..base import ObservableRdmTable, RowAction, TableConfig
from ..i18n import _
from ..protocol import RdmDataSource


class ActionButtonTable(ObservableRdmTable):
    """Table with action buttons per row.

    Uses native HTML table elements with rdm-* CSS classes.
    Action rendering is delegated to RowAction.render().

    Args:
        data_source: RdmDataSource (typically a Store)
        config: TableConfig with column definitions and custom_actions
        state: Shared state dict
        filter_by: Optional filter dict for data loading
        on_add: Callback when Add button clicked
        on_edit: Callback when Edit button clicked, receives row dict
        on_delete: Callback when Delete button clicked, receives row dict
    """

    def __init__(
        self,
        data_source: RdmDataSource,
        config: TableConfig,
        state: dict | None = None,
        *,
        filter_by: dict[str, Any] | None = None,
        on_add: Callable[[], Awaitable[None] | None] | None = None,
        on_edit: Callable[[dict], Awaitable[None] | None] | None = None,
        on_delete: Callable[[dict], Awaitable[None] | None] | None = None,
        render_toolbar: Callable[[], None] | None = None,
        auto_observe: bool = True,
    ):
        super().__init__(
            data_source=data_source, config=config, state=state,
            filter_by=filter_by, on_add=on_add,
            render_toolbar=render_toolbar, auto_observe=auto_observe,
        )
        # Build unified actions list from config and callbacks
        self._all_actions: list[RowAction] = list(config.custom_actions)
        if config.show_edit_button:
            self._all_actions.append(RowAction(icon="pencil", tooltip=_("Edit"), color="default", callback=on_edit))
        if config.show_delete_button:
            self._all_actions.append(RowAction(icon="trash", tooltip=_("Delete"), color="default", callback=on_delete))

    @ui.refreshable_method
    async def build(self):
        """Build the table using native HTML elements."""
        await self.load_data()
        self._build_toolbar("top")

        with html.div().classes("rdm-table-card rdm-component show-refresh"):
            with html.table().classes("rdm-table"):
                # Header
                with html.thead():
                    with html.tr():
                        for col in self.config.columns:
                            th = html.th(col.label or col.name)
                            if col.width_percent:
                                th.style(f"width: {col.width_percent}%")
                        # Actions column header
                        if self._all_actions:
                            html.th("").classes("rdm-col-actions")

                # Body
                with html.tbody():
                    if not self.data:
                        with html.tr():
                            colspan = len(self.config.columns)
                            if self._all_actions:
                                colspan += 1
                            with html.td().props(f"colspan={colspan}"):
                                ui.label(
                                    self.config.empty_message or _("No data")
                                ).classes("rdm-text-muted")
                    else:
                        for row in self.data:
                            self._build_row(row)

        self._build_toolbar("bottom")

    def _build_row(self, row: dict):
        """Build a single data row."""
        with html.tr():
            # Data columns
            for col in self.config.columns:
                with html.td():
                    self._render_cell(col, row.get(col.name, ""), row)

            # Action buttons column
            if self._all_actions:
                with html.td().classes("rdm-col-actions"):
                    with html.div().classes("rdm-actions"):
                        row_id = row.get("id", "")
                        for i, action in enumerate(self._all_actions):
                            action.render(row, mark=f"rdm-action-{i}-{row_id}")
