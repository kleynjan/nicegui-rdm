"""
EditDialog - Standalone modal dialog for add/edit operations.

A reusable modal dialog configured via Column definitions (dialog_columns).
Can be used independently or wired to any table component via callbacks.
"""
from typing import Any, Awaitable, Callable

from nicegui import html, ui

from .i18n import _
from .base import ClientComponent, Column
from .fields import build_form_field
from .protocol import RdmDataSource


class EditDialog(ClientComponent):
    """Standalone modal dialog for add/edit operations.

    Configured via Column definitions for form fields.
    Saves via RdmDataSource or custom callbacks.

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
        super().__init__()
        self.data_source = data_source
        self.columns = columns
        self.dialog_class = dialog_class
        self.title_add = title_add or _("Add")
        self.title_edit = title_edit or _("Edit")
        self.on_save = on_save
        self.on_cancel = on_cancel
        self.state: dict[str, Any] = {}
        self._current_item_id: int | None = None
        self._dialog: ui.dialog | None = None
        self._is_edit: bool = False

    def _init_state(self, item: dict | None = None):
        """Initialize state from item or defaults."""
        self.state = {}
        for col in self.columns:
            if item:
                value = item.get(col.name, col.default_value)
                if col.ui_type == ui.number:
                    self.state[col.name] = value
                else:
                    self.state[col.name] = value or ""
            else:
                self.state[col.name] = col.default_value

    def open_add(self):
        """Open dialog for adding a new item."""
        self._init_state()
        self._current_item_id = None
        self._is_edit = False
        self._show()

    def open_edit(self, item: dict):
        """Open dialog for editing an existing item."""
        self._init_state(item)
        self._current_item_id = item.get("id")
        self._is_edit = True
        self._show()

    def _show(self):
        """Build and show the modal dialog."""
        title = self.title_edit if self._is_edit else self.title_add

        with ui.dialog() as dlg:
            with html.div().classes("rdm-dialog-backdrop"):
                with html.div().classes(f"rdm-dialog {self.dialog_class or ''}"):
                    # Header
                    with html.div().classes("rdm-dialog-header"):
                        ui.label(title).classes("rdm-dialog-title")
                        with html.button().classes("rdm-dialog-close").on("click", self._handle_cancel):
                            html.i().classes("bi bi-x-lg")

                    # Body - form fields
                    with html.div().classes("rdm-dialog-body"):
                        for col in self.columns:
                            build_form_field(col, self.state)

                    # Footer - action buttons
                    with html.div().classes("rdm-dialog-footer"):
                        with html.button().classes("rdm-btn rdm-btn-primary").on(
                            "click", self._handle_save
                        ):
                            html.span(_("Save") if self._is_edit else _("Add"))
                        with html.button().classes("rdm-btn rdm-btn-secondary").on(
                            "click", self._handle_cancel
                        ):
                            html.span(_("Cancel"))

        self._dialog = dlg
        dlg.open()

    def _handle_cancel(self):
        """Handle cancel button click."""
        if self._dialog:
            self._dialog.close()
        if self.on_cancel:
            self.on_cancel()

    async def _handle_save(self):
        """Handle save button click."""
        # Build item data
        item_data = {}
        for col in self.columns:
            value = self.state.get(col.name, "")
            if isinstance(value, str):
                value = value.strip() or None
            item_data[col.name] = value

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
            if self._dialog:
                self._dialog.close()
            # Call on_save callback
            if self.on_save:
                result = self.on_save(saved_item)
                if result is not None and hasattr(result, '__await__'):
                    await result
