"""
DataTable - Primary editable table with modal dialog for add/edit.

Uses native HTML <table> elements for clean, semantic markup.
Edit operations happen via a modal dialog.
"""
from typing import Any

from nicegui import html, ui

from .i18n import _
from .base import TableConfig
from .fields import build_form_field
from ._table_base import BaseCrudTable
from .protocol import CrudDataSource


class DataTable(BaseCrudTable):
    """Primary editable table with modal dialog for add/edit operations.

    Uses native HTML table elements with nc-* CSS classes.
    Displays data in read-only table format, with Edit/Delete buttons per row.
    Add/Edit operations open a modal dialog.

    Args:
        state: Shared state dict
        data_source: CrudDataSource (typically a Store)
        config: TableConfig with column definitions
    """

    def __init__(self, state: dict, data_source: CrudDataSource, config: TableConfig):
        super().__init__(state, data_source, config)
        self.dialog_state: dict[str, Any] = {}
        self._current_item_id: int | None = None
        self._dialog: ui.dialog | None = None

    def _render_cell(self, col, value, row: dict):
        """Render a single cell value."""
        if col.render:
            col.render(row)
        else:
            display = col.formatter(value) if col.formatter else str(value) if value else ""
            html.span(display)

    @ui.refreshable
    async def build(self):
        """Build the table using native HTML elements."""
        await self.load_data()

        with html.div().classes("nc-table-card nc-component"):
            with html.table().classes("nc-table"):
                # Header
                with html.thead():
                    with html.tr():
                        for col in self.config.table_columns:
                            th = html.th(col.label or col.name)
                            if col.width_percent:
                                th.style(f"width: {col.width_percent}%")
                        # Actions column header
                        if self.config.show_edit_button or self.config.show_delete_button:
                            html.th("").classes("nc-col-actions")

                # Body
                with html.tbody():
                    if not self.data:
                        with html.tr():
                            colspan = len(self.config.table_columns)
                            if self.config.show_edit_button or self.config.show_delete_button:
                                colspan += 1
                            with html.td().props(f"colspan={colspan}"):
                                html.span(
                                    self.config.empty_message or _("No data")
                                ).classes("nc-text-muted")
                    else:
                        for row in self.data:
                            self._build_row(row)

    def _build_row(self, row: dict):
        """Build a single data row."""
        with html.tr():
            # Data columns
            for col in self.config.table_columns:
                with html.td():
                    self._render_cell(col, row.get(col.name, ""), row)

            # Action buttons column
            if self.config.show_edit_button or self.config.show_delete_button or self.config.custom_actions:
                with html.td().classes("nc-col-actions"):
                    with html.div().classes("nc-actions"):
                        # Custom actions first
                        for action in self.config.custom_actions:
                            btn = html.button().classes("nc-btn nc-btn-icon").on(
                                "click", lambda _, r=row, a=action: self._handle_custom_action(a, r)
                            )
                            with btn:
                                html.i().classes(f"bi bi-{action.icon}")
                            if action.tooltip:
                                btn.props(f'title="{action.tooltip}"')

                        # Edit button
                        if self.config.show_edit_button:
                            with html.button().classes("nc-btn nc-btn-icon").on(
                                "click", lambda _, r=row: self._open_edit_dialog(r)
                            ):
                                html.i().classes("bi bi-pencil")

                        # Delete button
                        if self.config.show_delete_button:
                            with html.button().classes("nc-btn nc-btn-icon").on(
                                "click", lambda _, r=row: self._handle_delete(r)
                            ):
                                html.i().classes("bi bi-trash")

    def render_add_button(self):
        """Render the add button - call from page code to position alongside other buttons."""
        if self.config.add_button and self.config.show_add_button:
            with html.button().classes("nc-btn nc-btn-primary").on(
                "click", self._open_add_dialog
            ):
                html.span(self.config.add_button)

    async def _handle_custom_action(self, action, row: dict):
        """Handle custom action button click."""
        if action.callback:
            result = action.callback(row)
            if hasattr(result, '__await__'):
                await result

    def _init_dialog_state(self, item: dict | None = None):
        """Initialize dialog_state from item or defaults."""
        self.dialog_state = {}
        for col in self.config.dialog_columns:
            if item:
                value = item.get(col.name, col.default_value)
                if col.ui_type == ui.number:
                    self.dialog_state[col.name] = value
                else:
                    self.dialog_state[col.name] = value or ""
            else:
                self.dialog_state[col.name] = col.default_value

    def _open_add_dialog(self):
        """Open dialog for adding new item."""
        self._init_dialog_state()
        self._show_dialog(is_edit=False)

    def _open_edit_dialog(self, item: dict):
        """Open dialog for editing existing item."""
        self._init_dialog_state(item)
        self._current_item_id = item.get("id")
        self._show_dialog(is_edit=True)

    def _show_dialog(self, is_edit: bool):
        """Build and show the modal dialog."""
        title = (self.config.dialog_title_edit if is_edit else self.config.dialog_title_add) or \
                (_("Edit") if is_edit else _("Add"))

        with ui.dialog() as dlg:
            with html.div().classes("nc-dialog-backdrop"):
                with html.div().classes(f"nc-dialog {self.config.dialog_class or ''}"):
                    # Header
                    with html.div().classes("nc-dialog-header"):
                        ui.label(title).classes("nc-dialog-title")
                        with html.button().classes("nc-dialog-close").on("click", dlg.close):
                            html.i().classes("bi bi-x-lg")

                    # Body - form fields
                    with html.div().classes("nc-dialog-body"):
                        for col in self.config.dialog_columns:
                            build_form_field(col, self.dialog_state)

                    # Footer - action buttons
                    with html.div().classes("nc-dialog-footer"):
                        with html.button().classes("nc-btn nc-btn-primary").on(
                            "click", lambda: self._handle_save(dlg, is_edit)
                        ):
                            html.span(_("Save") if is_edit else _("Add"))
                        with html.button().classes("nc-btn nc-btn-secondary").on(
                            "click", dlg.close
                        ):
                            html.span(_("Cancel"))

        self._dialog = dlg
        dlg.open()

    async def _handle_save(self, dialog, is_edit: bool):
        """Handle save button click in dialog."""
        # Build item data
        item_data = {}
        for col in self.config.dialog_columns:
            value = self.dialog_state.get(col.name, "")
            if isinstance(value, str):
                value = value.strip() or None
            item_data[col.name] = value

        # Validate
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
        """Handle delete button click."""
        await self._delete(item)


# Backwards compatibility alias
ModalEditTable = DataTable
