"""
DetailCard - read-only detail view with inline actions.

Renders item content via a render callback inside a structured header/body layout.
Edit/Delete action buttons sit inline in the header row (right-aligned), so any
extended body content (sub-tables, related lists) does not push them to the bottom.

No observer integration — the caller (ViewStack or page-level observer) handles refresh.
"""
from typing import Awaitable, Callable

from nicegui import html

from ..i18n import _
from ..base import RdmComponent, confirm_dialog
from ..protocol import RdmDataSource


class DetailCard(RdmComponent):
    """Read-only detail card with structured header/body layout.

    Layout:
        div.rdm-detail.rdm-component
          div.rdm-detail-header          ← flex row
            div.rdm-detail-title-group   ← render(item) output (flex:1)
            div.rdm-detail-actions       ← Edit / Delete buttons (right-aligned)
          [render_body(item) output]     ← optional extended content (sub-tables etc.)

    Args:
        state: External state dict (from ui_state). Key: 'item'.
        data_source: Used for delete operations.
        render: Async callback rendering header/summary content (title, key fields).
        render_body: Optional async callback for extended content below the header.
        on_edit: Called with item when Edit is clicked (typically vs.show_edit_existing).
        on_deleted: Called (no args) after successful delete (typically vs.show_list).
        show_edit: Whether to show the Edit button.
        show_delete: Whether to show the Delete button.
    """

    def __init__(
        self,
        state: dict,
        data_source: RdmDataSource,
        render: Callable[[dict], Awaitable[None]],
        render_body: Callable[[dict], Awaitable[None]] | None = None,
        on_edit: Callable[[dict], None] | None = None,
        on_deleted: Callable[[], None] | None = None,
        show_edit: bool = True,
        show_delete: bool = True,
    ):
        super().__init__(data_source)
        self.state = state
        self.state.setdefault("item", None)
        self._render = render
        self._render_body = render_body
        self.on_edit = on_edit
        self.on_deleted = on_deleted
        self.show_edit = show_edit
        self.show_delete = show_delete

    def set_item(self, item: dict | None):
        """Set the item to display."""
        self.state["item"] = item

    async def _handle_delete(self):
        item = self.state["item"]
        if item and await self._delete(item):
            if self.on_deleted:
                self.on_deleted()

    async def build(self):
        item = self.state["item"]
        if item is None:
            return

        show_actions = (self.show_edit and self.on_edit) or (self.show_delete and self.on_deleted)

        with html.div().classes("rdm-detail rdm-component"):
            with html.div().classes("rdm-detail-header"):
                with html.div().classes("rdm-detail-title-group"):
                    await self._render(item)
                if show_actions:
                    with html.div().classes("rdm-detail-actions"):
                        if self.show_edit and self.on_edit:
                            with html.button().classes("rdm-btn rdm-btn-primary").on(
                                "click", lambda _, i=item: self.on_edit(i)  # type: ignore[misc]
                            ):
                                html.span(_("Edit"))
                        if self.show_delete and self.on_deleted:
                            with html.button().classes("rdm-btn rdm-btn-danger").on(
                                "click", self._handle_delete
                            ):
                                html.span(_("Delete"))
            if self._render_body:
                await self._render_body(item)
