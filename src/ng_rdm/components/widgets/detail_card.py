"""
DetailCard - read-only detail view with item actions.

Renders item attributes via render_summary, then action buttons (Edit/Delete),
then optional related content (sub-tables, linked items) via render_related.

No observer integration — the caller (ViewStack or page-level observer) handles refresh.
"""
from typing import Awaitable, Callable

from nicegui import html

from ..base import RdmComponent, confirm_dialog
from ..i18n import _
from ..protocol import RdmDataSource
from .button import Button


class DetailCard(RdmComponent):
    """Read-only detail card with summary / actions / related layout.

    Args:
        state: External state dict (from ui_state). Key: 'item'.
        data_source: Used for delete operations.
        render_summary: Async callback rendering item attributes (title, key fields).
        render_related: Optional async callback for extended content (sub-tables etc.).
        on_edit: Called with item when Edit is clicked (typically vs.show_edit_existing).
        on_delete: Optional async callback(item). When provided, replaces the default
            `data_source.delete_item(item)` call — DetailCard still runs the
            confirmation dialog and success notification, but the caller handles
            the actual persistence (e.g. a cross-store cascade helper).
        on_deleted: Called (no args) after successful delete (typically vs.show_list).
        show_edit: Whether to show the Edit button.
        show_delete: Whether to show the Delete button.

    Layout:
        div.rdm-detail.rdm-component
          div.rdm-detail-summary         ← container for item attributes + detail action buttons
            [render_summary(item)]       ← rendered directly (no inner wrapper)
            div.rdm-detail-actions       ← Edit / Delete buttons
          div.rdm-detail-related         ← optional extended content below the summary (sub-tables etc.)
            [render_related(item)]
    """

    def __init__(
        self,
        data_source: RdmDataSource,
        render_summary: Callable[[dict], Awaitable[None]],
        state: dict | None = None,
        *,
        render_related: Callable[[dict], Awaitable[None]] | None = None,
        on_edit: Callable[[dict], None] | None = None,
        on_delete: Callable[[dict], Awaitable[None]] | None = None,
        on_deleted: Callable[[], None] | None = None,
        show_edit: bool = True,
        show_delete: bool = True,
    ):
        super().__init__(data_source)
        self.state = state if state is not None else {}
        self.state.setdefault("item", None)
        self._render_summary = render_summary
        self._render_related = render_related
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_deleted = on_deleted
        self.show_edit = show_edit
        self.show_delete = show_delete

    def set_item(self, item: dict | None):
        """Set the item to display."""
        self.state["item"] = item

    async def _handle_delete(self):
        item = self.state["item"]
        if item is None:
            return
        if self.on_delete is not None:
            if not await confirm_dialog(item):
                return
            try:
                await self.on_delete(item)
            except Exception as e:
                self._notify(str(e), type="negative")
                return
            self._notify(_("Item deleted"), type="info")
            if self.on_deleted:
                self.on_deleted()
            return
        if await self._delete(item) and self.on_deleted:
            self.on_deleted()

    async def build(self):
        item = self.state["item"]
        if item is None:
            return

        can_delete = self.show_delete and (self.on_delete is not None or self.on_deleted is not None)
        show_actions = (self.show_edit and self.on_edit) or can_delete

        with html.div().classes("rdm-detail rdm-component"):
            with html.div().classes("rdm-detail-summary"):
                await self._render_summary(item)
                if show_actions:
                    with html.div().classes("rdm-detail-actions"):
                        if self.show_edit and self.on_edit:
                            Button(_("Edit"), on_click=lambda _, i=item: self.on_edit(i))  # type: ignore[misc]
                        if can_delete:
                            Button(_("Delete"), color="danger", on_click=self._handle_delete)
            if self._render_related:
                with html.div().classes("rdm-detail-related"):
                    await self._render_related(item)
