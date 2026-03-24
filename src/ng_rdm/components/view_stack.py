"""
ViewStack - coordinator for list → detail → edit in-place navigation.

Manages visibility of three views (list, detail, edit) in a single viewport slot,
renders breadcrumb navigation, and wires up transitions between views.
"""
from typing import Any, Awaitable, Callable

from nicegui import html, ui

from .i18n import _
from .base import RdmComponent, TableConfig, confirm_dialog
from .detail import DetailCard
from .edit_card import EditCard
from .list import ListTable
from .protocol import RdmDataSource
from ..store import StoreEvent


class ViewStack(RdmComponent):
    """Coordinates list/detail/edit views with breadcrumb navigation.

    Usage:
        stack = ViewStack(
            data_source=store,
            select_config=select_cfg,
            detail_config=detail_cfg,
            render_detail=my_render_fn,
            breadcrumb_root="Roles",
            item_label=lambda item: item.get("name", ""),
        )
        await stack.build()
    """

    def __init__(
        self,
        data_source: RdmDataSource,
        select_config: TableConfig,
        detail_config: TableConfig,
        render_detail: Callable[[dict], Awaitable[None]],
        breadcrumb_root: str = "",
        item_label: Callable[[dict], str] = lambda item: str(item.get("name", "")),
        show_add: bool = True,
        show_edit: bool = True,
        show_delete: bool = True,
        detail_footer: Callable[[dict], Awaitable[None]] | None = None,
        list_footer: Callable[[], Awaitable[None]] | None = None,
        on_add: Callable[[], Awaitable[None] | None] | None = None,
    ):
        super().__init__(data_source)
        self.select_config = select_config
        self.detail_config = detail_config
        self.render_detail = render_detail
        self.breadcrumb_root = breadcrumb_root
        self.item_label = item_label
        self.show_add = show_add
        self.show_edit = show_edit
        self.show_delete = show_delete
        self.detail_footer = detail_footer
        self.list_footer = list_footer
        self.on_add = on_add

        # State: "list", "detail", or "edit"
        self._view: str = "list"
        self._item: dict | None = None

        # Shared state dicts for child components
        self._select_state: dict[str, Any] = {}
        self._detail_state: dict[str, Any] = {}

        self._table: ListTable | None = None
        self._detail: DetailCard | None = None
        self._edit: EditCard | None = None

    # ── Navigation ──

    def show_list(self):
        self._view = "list"
        self._item = None
        if self._detail:
            self._detail.set_item(None)
        self.build.refresh()  # type: ignore

    def show_detail(self, item: dict):
        self._view = "detail"
        self._item = item
        if self._detail:
            self._detail.set_item(item)
        self.build.refresh()  # type: ignore

    def show_edit_existing(self, item: dict | None = None):
        item = item or self._item
        if item is None:
            return
        self._view = "edit"
        self._item = item
        if self._edit:
            self._edit.set_item(item)
        self.build.refresh()  # type: ignore

    def show_edit_new(self):
        self._view = "edit"
        self._item = None
        if self._edit:
            self._edit.set_item(None)
        self.build.refresh()  # type: ignore

    # ── Callbacks ──

    def _on_row_selected(self, row_id: int | None):
        if row_id is None:
            return
        if self._table is None:
            return
        item = next((r for r in self._table.data if r.get("id") == row_id), None)
        if item:
            self.show_detail(item)

    def _on_edit_saved(self, saved_item: dict):
        self.show_detail(saved_item)

    def _on_edit_cancel(self):
        if self._item:
            self.show_detail(self._item)
        else:
            self.show_list()

    async def _on_delete(self):
        if self._item is None:
            return
        confirmed = await confirm_dialog(self._item)
        if confirmed:
            await self.data_source.delete_item(self._item)
            self._notify(_("Item deleted"), type="info")
            self.show_list()

    async def _on_store_change(self, event: StoreEvent):
        """Refresh detail view if the current item was updated or deleted."""
        if self._item is None:
            return
        item_id = self._item.get("id")
        if event.verb == "delete" and event.item.get("id") == item_id:
            self.show_list()
        elif event.verb == "update" and event.item.get("id") == item_id:
            items = await self.data_source.read_items(
                filter_by={"id": item_id},
                join_fields=self.detail_config.join_fields,
            )
            if items:
                self._item = items[0]
                if self._view == "detail" and self._detail:
                    self._detail.set_item(self._item)

    # ── Breadcrumb ──

    def _build_breadcrumb(self):
        with html.div().classes("rdm-breadcrumb rdm-component"):
            if self._view == "list":
                html.span("")
            else:
                with html.button().classes("rdm-btn rdm-btn-icon rdm-breadcrumb-back").on(
                    "click", self._breadcrumb_back
                ):
                    html.i().classes("bi bi-arrow-left")
                html.span(self.breadcrumb_root).classes("rdm-breadcrumb-item rdm-link").on(
                    "click", lambda: self.show_list()
                )
                if self._item:
                    html.span("›").classes("rdm-breadcrumb-separator")
                    label_text = self.item_label(self._item)
                    if self._view == "edit":
                        html.span(label_text).classes("rdm-breadcrumb-item rdm-link").on(
                            "click", lambda: self.show_detail(self._item)  # type: ignore
                        )
                    else:
                        html.span(label_text).classes("rdm-breadcrumb-item rdm-current")
                elif self._view == "edit":
                    html.span("›").classes("rdm-breadcrumb-separator")
                    html.span(_("New")).classes("rdm-breadcrumb-item rdm-current")

    def _breadcrumb_back(self):
        if self._view == "edit" and self._item:
            self.show_detail(self._item)
        else:
            self.show_list()

    # ── Build ──

    @ui.refreshable
    async def build(self):
        self._build_breadcrumb()

        if self._view == "list":
            await self._build_list_view()
        elif self._view == "detail":
            await self._build_detail_view()
        elif self._view == "edit":
            await self._build_edit_view()

    async def _build_list_view(self):
        self._table = ListTable(
            state=self._select_state,
            data_source=self.data_source,
            config=self.select_config,
            on_click=self._on_row_selected,
        )
        await self._table.build()  # type: ignore

        # Toolbar with add button and optional list_footer content
        with html.div().classes("rdm-view-stack-toolbar"):
            if self.show_add:
                add_handler = self.on_add if self.on_add else self.show_edit_new
                with html.button().classes("rdm-btn rdm-btn-primary").on("click", add_handler):
                    html.span(self.select_config.add_button or _("Add new"))

            if self.list_footer:
                await self.list_footer()

    async def _build_detail_view(self):
        with html.div().classes('rdm-card rdm-component'):
            with html.div().classes('rdm-detail-outer'):
                self._detail = DetailCard(
                    state=self._detail_state,
                    data_source=self.data_source,
                    config=self.detail_config,
                    render=self.render_detail,
                    show_edit=False,
                    show_delete=False,
                )
                self._detail.set_item(self._item)
                await self._detail.build()  # type: ignore

                with html.div().classes("rdm-detail-actions"):
                    if self.show_edit:
                        with html.button().classes("rdm-btn rdm-btn-primary").on(
                            "click", lambda: self.show_edit_existing()
                        ):
                            html.span(_("Edit"))
                    if self.show_delete:
                        with html.button().classes("rdm-btn rdm-btn-secondary").on(
                            "click", self._on_delete
                        ):
                            html.span(_("Delete"))

        if self.detail_footer and self._item:
            await self.detail_footer(self._item)

    async def _build_edit_view(self):
        self._edit = EditCard(
            data_source=self.data_source,
            config=self.detail_config,
            on_saved=self._on_edit_saved,
            on_cancel=self._on_edit_cancel,
        )
        self._edit.set_item(self._item)
        await self._edit.build()  # type: ignore
