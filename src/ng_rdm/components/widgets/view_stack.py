"""
ViewStack - navigation coordinator for list / detail / edit views.

Manages view switching and back navigation. Does NOT create child components —
the consumer provides render callbacks for each view.
"""
from typing import Awaitable, Callable

from nicegui import html, ui


class ViewStack:
    """Coordinates list/detail/edit views with back-arrow navigation.

    The consumer provides three render callbacks that build the actual UI
    for each view. ViewStack handles view state and back navigation.

    The list panel is rendered once and its visibility is toggled via NiceGUI
    bindings, so the list component (and its store observer) stays alive while
    navigating to detail/edit — back-navigation is instant with no re-query.

    Args:
        state: External state dict (from ui_state). Keys: 'view', 'item'.
        render_list: Async callback to render the list view. Receives the ViewStack.
        render_detail: Async callback to render the detail view. Receives (ViewStack, item).
        render_edit: Async callback to render the edit view. Receives (ViewStack, item|None).
    """

    def __init__(
        self,
        state: dict,
        render_list: Callable[["ViewStack"], Awaitable[None]],
        render_detail: Callable[["ViewStack", dict], Awaitable[None]],
        render_edit: Callable[["ViewStack", dict | None], Awaitable[None]],
    ):
        self.state = state
        self.state.setdefault("view", "list")
        self.state.setdefault("item", None)

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

    def show_detail(self, item: dict):
        self.state["view"] = "detail"
        self.state["item"] = item
        self._content.refresh()  # type: ignore[attr-defined]

    def show_edit_existing(self, item: dict | None = None):
        item = item or self.state["item"]
        if item is None:
            return
        self.state["view"] = "edit"
        self.state["item"] = item
        self._content.refresh()  # type: ignore[attr-defined]

    def show_edit_new(self):
        self.state["view"] = "edit"
        self.state["item"] = None
        self._content.refresh()  # type: ignore[attr-defined]

    def go_back(self):
        if self.state["view"] == "edit" and self.state["item"]:
            self.show_detail(self.state["item"])
        else:
            self.show_list()

    # ── Active content (detail or edit) ──

    @ui.refreshable_method
    async def _content(self):
        view = self.state["view"]
        item = self.state["item"]
        if view == "detail":
            assert item is not None
            await self._render_detail(self, item)
        elif view == "edit":
            await self._render_edit(self, item)

    # ── Build ──

    async def build(self):
        # List panel: rendered once, binding-driven visibility.
        # The list component's store observer stays alive while hidden,
        # so navigating back is instant with no re-query.
        with html.div() as list_panel:
            await self._render_list(self)
        list_panel.bind_visibility_from(self.state, "view", value="list")

        # Non-list panel: back arrow + content wrapper.
        with html.div().classes("rdm-view-stack-panel") as panel:
            with html.button().classes("rdm-back-nav rdm-btn rdm-btn-icon").on("click", self.go_back):
                html.i().classes("bi bi-arrow-left")
            with html.div().classes("rdm-view-stack-content"):
                await self._content()
        panel.bind_visibility_from(self.state, "view", backward=lambda v: v != "list")
