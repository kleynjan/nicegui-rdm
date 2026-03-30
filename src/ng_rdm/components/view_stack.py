"""
ViewStack - navigation coordinator for list / detail / edit views.

Manages view switching and breadcrumb rendering. Does NOT create child components —
the consumer provides render callbacks for each view.
"""
from typing import Awaitable, Callable

from nicegui import html, ui

from .i18n import _


class ViewStack:
    """Coordinates list/detail/edit views with breadcrumb navigation.

    The consumer provides three render callbacks that build the actual UI
    for each view. ViewStack handles view state and breadcrumb rendering.

    The list panel is rendered once and its visibility is toggled via NiceGUI
    bindings, so the list component (and its store observer) stays alive while
    navigating to detail/edit — back-navigation is instant with no re-query.

    Args:
        state: External state dict (from ui_state). Keys: 'view', 'item'.
        breadcrumb_root: Label for the root breadcrumb link (e.g. "Roles").
        item_label: Extracts a display label from an item for breadcrumbs.
        render_list: Async callback to render the list view. Receives the ViewStack.
        render_detail: Async callback to render the detail view. Receives (ViewStack, item).
        render_edit: Async callback to render the edit view. Receives (ViewStack, item|None).
    """

    def __init__(
        self,
        state: dict,
        breadcrumb_root: str,
        item_label: Callable[[dict], str],
        render_list: Callable[["ViewStack"], Awaitable[None]],
        render_detail: Callable[["ViewStack", dict], Awaitable[None]],
        render_edit: Callable[["ViewStack", dict | None], Awaitable[None]],
    ):
        self.state = state
        self.state.setdefault("view", "list")
        self.state.setdefault("item", None)

        self.breadcrumb_root = breadcrumb_root
        self.item_label = item_label
        self._render_list = render_list
        self._render_detail = render_detail
        self._render_edit = render_edit

    # ── Properties ──

    @property
    def view(self) -> str:
        return self.state["view"]

    @property
    def item(self) -> dict | None:
        return self.state["item"]

    # ── Navigation ──

    def show_list(self):
        self.state["view"] = "list"
        self.state["item"] = None
        self._breadcrumb.refresh()  # type: ignore[attr-defined]

    def show_detail(self, item: dict):
        self.state["view"] = "detail"
        self.state["item"] = item
        self._breadcrumb.refresh()  # type: ignore[attr-defined]
        self._detail_edit.refresh()  # type: ignore[attr-defined]

    def show_edit_existing(self, item: dict | None = None):
        item = item or self.state["item"]
        if item is None:
            return
        self.state["view"] = "edit"
        self.state["item"] = item
        self._breadcrumb.refresh()  # type: ignore[attr-defined]
        self._detail_edit.refresh()  # type: ignore[attr-defined]

    def show_edit_new(self):
        self.state["view"] = "edit"
        self.state["item"] = None
        self._breadcrumb.refresh()  # type: ignore[attr-defined]
        self._detail_edit.refresh()  # type: ignore[attr-defined]

    # ── Breadcrumb ──

    @ui.refreshable_method
    def _breadcrumb(self):
        with html.div().classes("rdm-breadcrumb rdm-component"):
            view = self.state["view"]
            item = self.state["item"]
            if view == "list":
                html.span("")
            else:
                with html.button().classes("rdm-btn rdm-btn-icon rdm-breadcrumb-back").on(
                    "click", self._breadcrumb_back
                ):
                    html.i().classes("bi bi-arrow-left")
                html.span(self.breadcrumb_root).classes("rdm-breadcrumb-item rdm-link").on(
                    "click", lambda: self.show_list()
                )
                if item:
                    html.span("›").classes("rdm-breadcrumb-separator")
                    label_text = self.item_label(item)
                    if view == "edit":
                        html.span(label_text).classes("rdm-breadcrumb-item rdm-link").on(
                            "click", lambda: self.show_detail(self.state["item"])  # type: ignore[arg-type]
                        )
                    else:
                        html.span(label_text).classes("rdm-breadcrumb-item rdm-current")
                elif view == "edit":
                    html.span("›").classes("rdm-breadcrumb-separator")
                    html.span(_("New")).classes("rdm-breadcrumb-item rdm-current")

    def _breadcrumb_back(self):
        if self.state["view"] == "edit" and self.state["item"]:
            self.show_detail(self.state["item"])
        else:
            self.show_list()

    # ── Detail / Edit content ──

    @ui.refreshable_method
    async def _detail_edit(self):
        view = self.state["view"]
        item = self.state["item"]
        if view == "detail":
            assert item is not None
            await self._render_detail(self, item)
        elif view == "edit":
            await self._render_edit(self, item)

    # ── Build ──

    async def build(self):
        self._breadcrumb()

        # List panel: rendered once, binding-driven visibility.
        # The list component's store observer stays alive while hidden,
        # so navigating back is instant with no re-query.
        with html.div() as list_panel:
            await self._render_list(self)
        list_panel.bind_visibility_from(self.state, "view", value="list")

        # Detail/edit panel: refreshes on each navigation (item changes).
        with html.div() as detail_panel:
            await self._detail_edit()
        detail_panel.bind_visibility_from(self.state, "view", backward=lambda v: v != "list")
