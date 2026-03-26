"""
DetailCard - store-connected detail view for a selected item.

Renders item details via a callback. Optionally shows Edit/Delete buttons
with configurable handlers. Auto-refreshes on store changes.
"""
from typing import Awaitable, Callable

from nicegui import html, ui

from .i18n import _
from .base import ObservableRdmComponent, TableConfig
from .protocol import RdmDataSource
from ..store import StoreEvent


class DetailCard(ObservableRdmComponent):
    """Detail card showing a selected item with optional action buttons.

    Uses a render callback for flexible layout — the callback receives
    the selected item dict and renders it however needed.
    """

    def __init__(
        self,
        state: dict,
        data_source: RdmDataSource,
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
        self.build.refresh()

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
        await self.build.refresh()

    async def _handle_delete(self):
        if self.selected_item is None:
            return
        item = self.selected_item
        deleted = await self._delete(item)
        if deleted:
            if self.on_delete:
                self.on_delete(item)
            self.selected_item = None

    @ui.refreshable_method
    async def build(self):
        if self.selected_item is None:
            return

        with html.div().classes("rdm-detail rdm-component show-refresh"):
            if self.render_callback:
                await self.render_callback(self.selected_item)

            if self.show_edit or self.show_delete:
                with html.div().classes("rdm-detail-actions"):
                    if self.show_edit and self.on_edit:
                        item = self.selected_item
                        with html.button().classes("rdm-btn rdm-btn-primary").on(
                            "click", lambda _, i=item: self.on_edit(i)  # type: ignore
                        ):
                            html.span(_(("Edit")))
                    if self.show_delete:
                        with html.button().classes("rdm-btn rdm-btn-danger").on(
                            "click", self._handle_delete
                        ):
                            html.span(_("Delete"))
