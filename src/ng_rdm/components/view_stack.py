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

    Args:
        breadcrumb_root: Label for the root breadcrumb link (e.g. "Roles").
        item_label: Extracts a display label from an item for breadcrumbs.
        render_list: Async callback to render the list view. Receives the ViewStack.
        render_detail: Async callback to render the detail view. Receives (ViewStack, item).
        render_edit: Async callback to render the edit view. Receives (ViewStack, item|None).
    """

    def __init__(
        self,
        breadcrumb_root: str,
        item_label: Callable[[dict], str],
        render_list: Callable[["ViewStack"], Awaitable[None]],
        render_detail: Callable[["ViewStack", dict], Awaitable[None]],
        render_edit: Callable[["ViewStack", dict | None], Awaitable[None]],
    ):
        self.breadcrumb_root = breadcrumb_root
        self.item_label = item_label
        self._render_list = render_list
        self._render_detail = render_detail
        self._render_edit = render_edit

        self._view: str = "list"
        self._item: dict | None = None

    # ── Properties ──

    @property
    def view(self) -> str:
        return self._view

    @property
    def item(self) -> dict | None:
        return self._item

    # ── Navigation ──

    def show_list(self):
        self._view = "list"
        self._item = None
        self.build.refresh()  # type: ignore[attr-defined]

    def show_detail(self, item: dict):
        self._view = "detail"
        self._item = item
        self.build.refresh()  # type: ignore[attr-defined]

    def show_edit_existing(self, item: dict | None = None):
        item = item or self._item
        if item is None:
            return
        self._view = "edit"
        self._item = item
        self.build.refresh()  # type: ignore[attr-defined]

    def show_edit_new(self):
        self._view = "edit"
        self._item = None
        self.build.refresh()  # type: ignore[attr-defined]

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
                            "click", lambda: self.show_detail(self._item)  # type: ignore[arg-type]
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
            await self._render_list(self)
        elif self._view == "detail":
            assert self._item is not None
            await self._render_detail(self, self._item)
        elif self._view == "edit":
            await self._render_edit(self, self._item)
