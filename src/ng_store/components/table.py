"""
DataTable - Primary editable table with configurable action rendering.

Uses native HTML <table> elements for clean, semantic markup.
Supports both icon and button styles for actions, with optional built-in modal editing.
"""
from typing import Any, Awaitable, Callable, Literal

from nicegui import html, ui

from .i18n import _
from .base import TableConfig
from .fields import build_form_field
from ._table_base import BaseCrudTable
from .protocol import CrudDataSource


class DataTable(BaseCrudTable):
    """Primary editable table with configurable action rendering.

    Uses native HTML table elements with nc-* CSS classes.
    Supports icon or button styles for Edit/Delete actions.
    Can use built-in modal dialog or delegate to external callbacks.

    Args:
        state: Shared state dict
        data_source: CrudDataSource (typically a Store)
        config: TableConfig with column definitions
        filter_by: Optional filter dict for data loading
        action_style: "icon" for icon buttons, "button" for text buttons
        on_edit: External callback when Edit clicked (if None, uses built-in modal)
        on_delete: External callback when Delete clicked (if None, uses internal delete)
        edit_label: Label for edit button (button style only)
        delete_label: Label for delete button (button style only)
    """

    def __init__(
        self,
        state: dict,
        data_source: CrudDataSource,
        config: TableConfig,
        filter_by: dict[str, Any] | None = None,
        action_style: Literal["icon", "button"] = "icon",
        on_edit: Callable[[dict], Awaitable[None] | None] | None = None,
        on_delete: Callable[[dict], Awaitable[None] | None] | None = None,
        edit_label: str | None = None,
        delete_label: str | None = None,
    ):
        super().__init__(state, data_source, config)
        self.filter_by = filter_by
        self.action_style = action_style
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.edit_label = edit_label or _("Edit")
        self.delete_label = delete_label or _("Delete")
        self.dialog_state: dict[str, Any] = {}
        self._current_item_id: int | None = None
        self._dialog: ui.dialog | None = None

    async def load_data(self, join_fields: list[str] | None = None):
        """Load data from store with filter and join fields from config."""
        self.data = await self.data_source.read_items(
            filter_by=self.filter_by,
            join_fields=join_fields or self.config.join_fields,
        )

    def _render_cell(self, col, value, row: dict):
        """Render a single cell value."""
        if col.render:
            col.render(row)
        elif col.on_click:
            raw_value = row.get(col.name, "") or ""
            display = col.formatter(raw_value) if col.formatter else str(raw_value)
            handler = col.on_click
            html.span(display).classes("nc-link").on(
                "click", lambda _, r=row, h=handler: h(r)
            )
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
                            self._render_custom_action(action, row)

                        # Edit button
                        if self.config.show_edit_button:
                            self._render_edit_button(row)

                        # Delete button
                        if self.config.show_delete_button:
                            self._render_delete_button(row)

    def _render_custom_action(self, action, row: dict):
        """Render a custom action button based on variant or action_style.

        Resolution:
        - If action.variant is set, use that style
        - Otherwise, follow table's action_style
        - Fall back to whatever is available (icon or label)
        """
        # Determine effective style
        if action.variant:
            effective_style = action.variant
        else:
            effective_style = self.action_style

        # Render based on style
        if effective_style == "icon" and action.icon:
            btn = html.button().classes("nc-btn nc-btn-icon").on(
                "click", lambda _, r=row, a=action: self._handle_custom_action(a, r)
            )
            with btn:
                html.i().classes(f"bi bi-{action.icon}")
            if action.tooltip:
                btn.props(f'title="{action.tooltip}"')
        elif effective_style in ("primary", "secondary", "danger") and action.label:
            # Explicit variant with label
            btn_class = f"nc-btn nc-btn-{effective_style} nc-btn-sm"
            with html.button().classes(btn_class).on(
                "click", lambda _, r=row, a=action: self._handle_custom_action(a, r)
            ):
                html.span(action.label)
        elif effective_style == "button" and action.label:
            # Generic button style - default to primary
            with html.button().classes("nc-btn nc-btn-primary nc-btn-sm").on(
                "click", lambda _, r=row, a=action: self._handle_custom_action(a, r)
            ):
                html.span(action.label)
        elif action.label:
            # Fallback: have label but no matching style, render as primary button
            with html.button().classes("nc-btn nc-btn-primary nc-btn-sm").on(
                "click", lambda _, r=row, a=action: self._handle_custom_action(a, r)
            ):
                html.span(action.label)
        elif action.icon:
            # Fallback: have icon but button style requested, render as icon anyway
            btn = html.button().classes("nc-btn nc-btn-icon").on(
                "click", lambda _, r=row, a=action: self._handle_custom_action(a, r)
            )
            with btn:
                html.i().classes(f"bi bi-{action.icon}")
            if action.tooltip:
                btn.props(f'title="{action.tooltip}"')

    def _render_edit_button(self, row: dict):
        """Render edit button based on action_style."""
        if self.action_style == "icon":
            with html.button().classes("nc-btn nc-btn-icon").on(
                "click", lambda _, r=row: self._handle_edit(r)
            ):
                html.i().classes("bi bi-pencil")
        else:
            with html.button().classes("nc-btn nc-btn-primary nc-btn-sm").on(
                "click", lambda _, r=row: self._handle_edit(r)
            ):
                html.span(self.edit_label)

    def _render_delete_button(self, row: dict):
        """Render delete button based on action_style."""
        if self.action_style == "icon":
            with html.button().classes("nc-btn nc-btn-icon").on(
                "click", lambda _, r=row: self._handle_delete(r)
            ):
                html.i().classes("bi bi-trash")
        else:
            with html.button().classes("nc-btn nc-btn-secondary nc-btn-sm").on(
                "click", lambda _, r=row: self._handle_delete(r)
            ):
                html.span(self.delete_label)

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

    async def _handle_edit(self, row: dict):
        """Handle edit button click - use callback or built-in modal."""
        if self.on_edit:
            result = self.on_edit(row)
            if result is not None and hasattr(result, '__await__'):
                await result
        else:
            self._open_edit_dialog(row)

    async def _handle_delete(self, item: dict):
        """Handle delete button click - use callback or internal delete."""
        if self.on_delete:
            result = self.on_delete(item)
            if result is not None and hasattr(result, '__await__'):
                await result
        else:
            await self._delete(item)

    # --- Built-in Modal Dialog (used when on_edit is not provided) ---

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


# Backwards compatibility aliases
ModalEditTable = DataTable
ActionButtonTable = DataTable
ActionTable = DataTable
