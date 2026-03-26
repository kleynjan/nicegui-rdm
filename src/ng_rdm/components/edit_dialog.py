"""
EditDialog - Standalone modal dialog for add/edit operations.

A reusable modal dialog configured via Column definitions (dialog_columns).
Can be used independently or wired to any table component via callbacks.
Uses the custom Dialog component for consistent styling and behavior.
"""
from typing import Any, Awaitable, Callable

from nicegui import html, ui

from .i18n import _
from .base import Column, RdmComponent
from .dialog import Dialog
from .fields import build_form_field
from .protocol import RdmDataSource


class EditDialog(RdmComponent):
    """Standalone modal dialog for add/edit operations.

    Configured via Column definitions for form fields.
    Saves via RdmDataSource or custom callbacks.
    Uses Dialog component with @ui.refreshable for efficient DOM reuse.

    Args:
        data_source: RdmDataSource for validation and save operations
        columns: List of Column definitions for form fields
        dialog_class: Optional CSS class for dialog styling
        title_add: Dialog title for add mode (default: "Add")
        title_edit: Dialog title for edit mode (default: "Edit")
        on_save: Optional callback after successful save, receives saved item
        on_cancel: Optional callback when dialog is cancelled
    """

    def __init__(
        self,
        data_source: RdmDataSource,
        columns: list[Column],
        dialog_class: str | None = None,
        title_add: str | None = None,
        title_edit: str | None = None,
        on_save: Callable[[dict], Awaitable[None] | None] | None = None,
        on_cancel: Callable[[], None] | None = None,
    ):
        super().__init__(data_source)
        self.columns = columns
        self.dialog_class = dialog_class or ""
        self.title_add = title_add or _("Add")
        self.title_edit = title_edit or _("Edit")
        self.on_save = on_save
        self.on_cancel = on_cancel
        self.state: dict[str, Any] = {}
        self._current_item_id: int | None = None
        self._dlg: Dialog | None = None
        self._content: Any = None
        self._is_edit: bool = False

    def open_add(self):
        """Open dialog for adding a new item."""
        self.state = self._init_form_state(self.columns)
        self._current_item_id = None
        self._is_edit = False
        self._show()

    def open_edit(self, item: dict):
        """Open dialog for editing an existing item."""
        self.state = self._init_form_state(self.columns, item)
        self._current_item_id = item.get("id")
        self._is_edit = True
        self._show()

    def _show(self):
        """Show the modal dialog, creating it lazily on first use."""
        if self._dlg is None:
            self._build()
        else:
            self._content.refresh()
        assert self._dlg is not None
        self._dlg.open()

    def _build(self):
        """Build the dialog structure once."""
        with Dialog(dialog_class=self.dialog_class, on_close=self._handle_cancel) as self._dlg:
            @ui.refreshable
            def _content():
                title = self.title_edit if self._is_edit else self.title_add
                assert self._dlg is not None

                # Header
                with html.div().classes("rdm-dialog-header"):
                    ui.label(title).classes("rdm-dialog-title")
                    with html.button().classes("rdm-dialog-close").on("click", self._dlg.close):
                        html.i().classes("bi bi-x-lg")

                # Form fields
                for col in self.columns:
                    build_form_field(col, self.state)

            self._content = _content
            _content()

            # Footer - action buttons (outside refreshable for stability)
            with self._dlg.actions():
                with html.button().classes("rdm-btn rdm-btn-primary").on(
                    "click", self._handle_save
                ):
                    html.span(_("Save"))
                with html.button().classes("rdm-btn rdm-btn-secondary").on(
                    "click", self._dlg.close
                ):
                    html.span(_("Cancel"))

    def _handle_cancel(self):
        """Handle cancel/close."""
        if self.on_cancel:
            self.on_cancel()

    async def _handle_save(self):
        """Handle save button click."""
        item_data = self._build_item_data(self.columns, self.state)

        # Validate
        (valid, error_dict) = self.data_source.validate(item_data)
        if not valid:
            self._notify(
                f"{error_dict['col_name']} {error_dict['error_value']}: {error_dict['error_msg']}",
                type="warning",
                timeout=1500,
            )
            return

        # Save
        if self._is_edit and self._current_item_id is not None:
            saved_item = await self.data_source.update_item(self._current_item_id, item_data)
            if saved_item:
                self._notify(_("Item updated"), type="positive")
        else:
            saved_item = await self.data_source.create_item(item_data)
            if saved_item:
                self._notify(_("Item created"), type="positive")

        if saved_item:
            if self._dlg:
                self._dlg.close()
            # Call on_save callback
            if self.on_save:
                result = self.on_save(saved_item)
                if result is not None and hasattr(result, '__await__'):
                    await result
