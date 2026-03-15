"""
Modal edit CRUD table - table view with modal dialogs for create/edit.
Uses div-based flexbox layout matching base.css .table-header/.table-row patterns.
"""

from typing import Any

from nicegui import ui

from .i18n import _
from .base import TableConfig
from .fields import build_form_field
from ._table_base import BaseCrudTable
from .protocol import CrudDataSource


class ModalEditTable(BaseCrudTable):
    """Modal edit mode - table view with modal dialogs for add/edit operations."""

    def __init__(self, state: dict, data_source: CrudDataSource, config: TableConfig):
        super().__init__(state, data_source, config)
        self.dialog_state: dict[str, Any] = {}
        self._current_item_id: int | None = None

    def _build_header(self):
        """Build header row using divs with base.css table-header pattern"""
        with ui.row().classes("table-header"):
            for column in self.config.table_columns:
                ui.label(column.label or column.name).classes(f"col-{column.name}").style(column.width_style)

    @ui.refreshable
    async def build(self):
        """Build the modal-edit table using divs with flexbox layout"""
        await self.load_data()
        with ui.card().classes("data-table"):
            self._build_header()
            self._build_body()

    def render_add_button(self):
        """Render the add button - call this from page code to position alongside other buttons."""
        if self.config.add_button:
            ui.button(self.config.add_button, on_click=self._open_add_dialog).classes("btn-primary")

    def _build_body(self):
        """Build data rows using divs with base.css table-row pattern"""
        if not self.data and self.config.empty_message:
            # Show empty state message
            with ui.row().classes("table-row"):
                ui.label(self.config.empty_message).classes("empty-state")
            return

        for row in self.data:
            with ui.row().classes("table-row"):
                # Data columns
                for col in self.config.table_columns:
                    value = row.get(col.name, "")
                    display = col.formatter(value) if col.formatter else str(value)
                    ui.label(display).classes(f"col-{col.name}").style(col.width_style)

                # Action buttons
                with ui.row().classes("col-actions"):
                    # Custom actions first
                    for action in self.config.custom_actions:
                        btn = ui.button(icon=action.icon, color="grey",
                                        on_click=lambda _, r=row, a=action: self._handle_custom_action(a, r)) \
                            .props("flat dense").classes("btn-icon")
                        if action.tooltip:
                            btn.tooltip(action.tooltip)
                    # Edit button
                    if self.config.show_edit_button:
                        ui.button(icon="edit", color="grey",
                                  on_click=lambda _, r=row: self._open_edit_dialog(r)) \
                            .props("flat dense").classes("btn-icon")
                    # Delete button
                    if self.config.show_delete_button:
                        ui.button(icon="delete", color="grey",
                                  on_click=lambda _, r=row: self._handle_delete(r)) \
                            .props("flat dense").classes("btn-icon")

    async def _handle_custom_action(self, action, row: dict):
        """Handle custom action button click"""
        if action.callback:
            result = action.callback(row)
            # If callback returns awaitable, await it
            if hasattr(result, '__await__'):
                await result

    def _init_dialog_state(self, item: dict | None = None):
        """Initialize dialog_state from item or defaults"""
        self.dialog_state = {}
        for col in self.config.dialog_columns:
            if item:
                value = item.get(col.name, col.default_value)
                # Only convert None to "" for text inputs; ui.number needs None
                if col.ui_type == ui.number:
                    self.dialog_state[col.name] = value
                else:
                    self.dialog_state[col.name] = value or ""
            else:
                self.dialog_state[col.name] = col.default_value

    def _open_add_dialog(self):
        """Open dialog for adding new item"""
        self._init_dialog_state()
        self._show_dialog(is_edit=False)

    def _open_edit_dialog(self, item: dict):
        """Open dialog for editing existing item"""
        self._init_dialog_state(item)
        self._current_item_id = item.get("id")
        self._show_dialog(is_edit=True)

    def _show_dialog(self, is_edit: bool):
        """Build and show the modal dialog"""
        dialog_class = f"dialog-card {self.config.dialog_class or ''}".strip()
        title = (self.config.dialog_title_edit if is_edit else self.config.dialog_title_add) or \
                ("Edit" if is_edit else "Add")

        with ui.dialog() as dlg, ui.card().tight().classes(dialog_class):
            ui.label(title).classes("dialog-header")

            for col in self.config.dialog_columns:
                build_form_field(col, self.dialog_state)

            # Action buttons
            with ui.row().classes("dialog-actions"):
                ui.button(_("Save") if is_edit else _("Add"),
                          on_click=lambda: self._handle_save(dlg, is_edit)).classes("btn-primary")
                ui.button(_("Cancel"), on_click=dlg.close).classes("btn-secondary")

        self._dialog = dlg
        dlg.open()

    async def _handle_save(self, dialog, is_edit: bool):
        """Handle save button click in dialog"""
        # Build item data, converting empty strings to None where appropriate
        item_data = {}
        for col in self.config.dialog_columns:
            value = self.dialog_state.get(col.name, "")
            # Convert empty strings to None (like groups.py does with `.strip() or None`)
            if isinstance(value, str):
                value = value.strip() or None
            item_data[col.name] = value

        # Validate using data source
        (valid, error_dict) = self._validate(item_data)
        if not valid:
            return

        if is_edit and self._current_item_id is not None:
            success = await self._update(self._current_item_id, item_data)
        else:
            success = await self._validate_and_create(item_data)

        if success:
            dialog.close()

    async def _handle_delete(self, item: dict):
        """Handle delete button click"""
        await self._delete(item)
