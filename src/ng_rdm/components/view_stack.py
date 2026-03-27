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
from .list_table import ListTable
from .protocol import RdmDataSource
from ..store import StoreEvent


class ViewStack(RdmComponent):
    """Coordinates master/detail/edit views with breadcrumb navigation.

    Args:
        data_source: RdmDataSource backing this stack.
        master_config: TableConfig for the master (list) view. Controls columns
            and add button presentation (show_add_button, add_button text).
        detail_config: TableConfig for the detail/edit views. Controls edit/delete
            buttons (show_edit_button/show_delete_button) and custom_actions
            for extra buttons in the detail toolbar.
        render_detail_item: Async callback that renders the detail card content.
            Receives the selected item dict.
        breadcrumb_root: Label for the root breadcrumb link (e.g. "Roles").
        item_label: Extracts a display label from an item for breadcrumbs.
        render_detail_sub: Optional async callback for subordinate content below
            the detail card (e.g. related tables, tabs). Receives item dict.
        on_master_add: Callback for the master list's add button.
            Defaults to show_edit_new (navigates to edit view for a new item).
        render_master_toolbar: Optional callable rendering extra buttons
            in the master list's toolbar (alongside the add button).

    Usage:
        stack = ViewStack(
            data_source=store,
            master_config=master_cfg,
            detail_config=detail_cfg,
            render_detail_item=my_render_fn,
            breadcrumb_root="Roles",
            item_label=lambda item: item.get("name", ""),
        )
        await stack.build()
    """

    def __init__(
        self,
        data_source: RdmDataSource,
        master_config: TableConfig,
        detail_config: TableConfig,
        render_detail_item: Callable[[dict], Awaitable[None]],
        breadcrumb_root: str = "",
        item_label: Callable[[dict], str] = lambda item: str(item.get("name", "")),
        render_detail_sub: Callable[[dict], Awaitable[None]] | None = None,
        on_master_add: Callable[[], Awaitable[None] | None] | None = None,
        render_master_toolbar: Callable[[], None] | None = None,
    ):
        super().__init__(data_source)
        self.master_config = master_config
        self.detail_config = detail_config
        self.render_detail_item = render_detail_item
        self.breadcrumb_root = breadcrumb_root
        self.item_label = item_label
        self.render_detail_sub = render_detail_sub
        self._on_master_add = on_master_add or self.show_edit_new
        self._render_master_toolbar = render_master_toolbar

        # State: "list", "detail", or "edit"
        self._view: str = "list"
        self._item: dict | None = None

        # Shared state dicts for child components
        self._master_state: dict[str, Any] = {}
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
        self.build.refresh()

    def show_detail(self, item: dict):
        self._view = "detail"
        self._item = item
        if self._detail:
            self._detail.set_item(item)
        self.build.refresh()    # type: ignore

    def show_edit_existing(self, item: dict | None = None):
        item = item or self._item
        if item is None:
            return
        self._view = "edit"
        self._item = item
        if self._edit:
            self._edit.set_item(item)
        self.build.refresh()

    def show_edit_new(self):
        self._view = "edit"
        self._item = None
        if self._edit:
            self._edit.set_item(None)
        self.build.refresh()    # type: ignore

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

    # NOTE: This method was never subscribed to any observer - dead code
    # async def _on_store_change(self, event: StoreEvent):
    #     """Refresh detail view if the current item was updated or deleted."""
    #     if self._item is None:
    #         return
    #     item_id = self._item.get("id")
    #     if event.verb == "delete" and event.item.get("id") == item_id:
    #         self.show_list()
    #     elif event.verb == "update" and event.item.get("id") == item_id:
    #         items = await self.data_source.read_items(
    #             filter_by={"id": item_id},
    #             join_fields=self.detail_config.join_fields,
    #         )
    #         if items:
    #             self._item = items[0]
    #             if self._view == "detail" and self._detail:
    #                 self._detail.set_item(self._item)

    # ── Detail action rendering ──

    def _render_detail_action(self, action):
        """Render a custom action button in the detail toolbar."""
        variant = action.variant or "primary"
        btn_class = f"rdm-btn rdm-btn-{variant}"
        item = self._item
        with html.button().classes(btn_class).on(
            "click", lambda _, i=item, a=action: a.callback(i) if a.callback else None
        ):
            if action.icon:
                html.i().classes(f"bi bi-{action.icon}")
            if action.label:
                html.span(action.label)

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

    @ui.refreshable_method
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
            state=self._master_state,
            data_source=self.data_source,
            config=self.master_config,
            on_click=self._on_row_selected,
            on_add=self._on_master_add,
            render_toolbar=self._render_master_toolbar,
        )
        await self._table.build()

    async def _build_detail_view(self):
        with html.div().classes('rdm-card rdm-component'):
            with html.div().classes('rdm-detail-outer'):
                self._detail = DetailCard(
                    state=self._detail_state,
                    data_source=self.data_source,
                    config=self.detail_config,
                    render=self.render_detail_item,
                    show_edit=False,
                    show_delete=False,
                )
                self._detail.set_item(self._item)
                await self._detail.build()

                with html.div().classes("rdm-detail-actions"):
                    if self.detail_config.show_edit_button:
                        with html.button().classes("rdm-btn rdm-btn-primary").on(
                            "click", lambda: self.show_edit_existing()
                        ):
                            html.span(_("Edit"))
                    if self.detail_config.show_delete_button:
                        with html.button().classes("rdm-btn rdm-btn-secondary").on(
                            "click", self._on_delete
                        ):
                            html.span(_("Delete"))
                    for action in self.detail_config.custom_actions:
                        self._render_detail_action(action)

        if self.render_detail_sub and self._item:
            await self.render_detail_sub(self._item)

    async def _build_edit_view(self):
        self._edit = EditCard(
            data_source=self.data_source,
            config=self.detail_config,
            on_saved=self._on_edit_saved,
            on_cancel=self._on_edit_cancel,
        )
        self._edit.set_item(self._item)
        await self._edit.build()
