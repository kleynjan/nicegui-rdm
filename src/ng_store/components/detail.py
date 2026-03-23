"""
DetailCard - store-connected detail view for a selected item.

Renders item details via a callback. Optionally shows Edit/Delete buttons
with configurable handlers. Auto-refreshes on store changes.
"""
from typing import Awaitable, Callable

from nicegui import html, ui

from .i18n import _
from .base import StoreComponent, TableConfig, confirm_dialog
from .protocol import CrudDataSource
from ..store import StoreEvent


class DetailCard(StoreComponent):
    """Detail card showing a selected item with optional action buttons.

    Uses a render callback for flexible layout — the callback receives
    the selected item dict and renders it however needed.
    """

    def __init__(
        self,
        state: dict,
        data_source: CrudDataSource,
        config: TableConfig,
        state_key: str = "selected_item",
        render: Callable[[dict], Awaitable[None]] | None = None,
        on_edit: Callable[[dict], None] | None = None,
        on_delete: Callable[[dict], None] | None = None,
        show_edit: bool = True,
        show_delete: bool = True,
    ):
        super().__init__(state, data_source)
        self.config = config
        self.state_key = state_key
        self.render_callback = render
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.show_edit = show_edit
        self.show_delete = show_delete

        if self.state_key not in self.state:
            self.state[self.state_key] = None

    @property
    def selected_item(self) -> dict | None:
        return self.state.get(self.state_key)

    @selected_item.setter
    def selected_item(self, value: dict | None):
        self.state[self.state_key] = value

    def set_item(self, item: dict | None):
        self.selected_item = item
        self.build.refresh()  # type: ignore

    async def _handle_datasource_change(self, event: StoreEvent):
        if self.selected_item is None:
            return
        item_id = self.selected_item.get("id")
        if event.verb == "delete" and event.item.get("id") == item_id:
            self.selected_item = None
        elif event.verb == "update" and event.item.get("id") == item_id:
            items = await self.data_source.read_items(
                filter_by={"id": item_id},
                join_fields=self.config.join_fields,
            )
            self.selected_item = items[0] if items else None
        await self.build.refresh()  # type: ignore

    async def _handle_delete(self):
        if self.selected_item is None:
            return
        confirmed = await confirm_dialog({
            'question': _('Delete this item?'),
            'explanation': _('This action cannot be undone.'),
            'no_button': _('Cancel'),
            'yes_button': _('Delete'),
        }, self.selected_item)
        if confirmed:
            await self.data_source.delete_item(self.selected_item)
            self._notify(_("Item deleted"), type="info")
            if self.on_delete:
                self.on_delete(self.selected_item)
            self.selected_item = None

    @ui.refreshable
    async def build(self):
        if self.selected_item is None:
            return

        with html.div().classes("nc-detail nc-component"):
            if self.render_callback:
                await self.render_callback(self.selected_item)

            if self.show_edit or self.show_delete:
                with html.div().classes("nc-detail-actions"):
                    if self.show_edit and self.on_edit:
                        item = self.selected_item
                        with html.button().classes("nc-btn nc-btn-primary").on(
                            "click", lambda _, i=item: self.on_edit(i)  # type: ignore
                        ):
                            html.span(_(("Edit")))
                    if self.show_delete:
                        with html.button().classes("nc-btn nc-btn-danger").on(
                            "click", self._handle_delete
                        ):
                            html.span(_("Delete"))
