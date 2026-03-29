"""
detail_card - render function for a detail view of a selected item.

Renders item details via a callback, with optional Edit/Delete action buttons.
No observer integration — the caller (ViewStack or page-level observer) handles refresh.
"""
from typing import Awaitable, Callable

from nicegui import html

from .i18n import _
from .base import confirm_dialog


async def detail_card(
    item: dict | None,
    render: Callable[[dict], Awaitable[None]],
    on_edit: Callable[[dict], None] | None = None,
    on_delete: Callable[[dict], Awaitable[None] | None] | None = None,
    show_edit: bool = True,
    show_delete: bool = True,
):
    """Render a detail view for an item with optional action buttons."""
    if item is None:
        return

    with html.div().classes("rdm-detail rdm-component"):
        await render(item)

        if (show_edit and on_edit) or (show_delete and on_delete):
            with html.div().classes("rdm-detail-actions"):
                if show_edit and on_edit:
                    with html.button().classes("rdm-btn rdm-btn-primary").on(
                        "click", lambda _, i=item: on_edit(i)  # type: ignore[misc]
                    ):
                        html.span(_("Edit"))
                if show_delete and on_delete:
                    with html.button().classes("rdm-btn rdm-btn-danger").on(
                        "click", lambda _, i=item: on_delete(i)  # type: ignore[misc]
                    ):
                        html.span(_("Delete"))
