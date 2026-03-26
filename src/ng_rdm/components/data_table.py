"""
DataTable - Primary editable table with configurable action rendering.

Uses native HTML <table> elements for clean, semantic markup.
Supports both icon and button styles for actions, with optional built-in modal editing.
Uses the custom Dialog component for consistent styling and behavior.
"""
from typing import Any, Awaitable, Callable, Literal

from nicegui import html, ui

from .i18n import _
from .base import ObservableRdmComponent, TableConfig
from .dialog import Dialog
from .fields import build_form_field
from .protocol import RdmDataSource


class DataTable(ObservableRdmComponent):
    """Primary editable table with configurable action rendering.

    Uses native HTML table elements with rdm-* CSS classes.
    Supports icon or button styles for Edit/Delete actions.
    Can use built-in modal dialog or delegate to external callbacks.

    Args:
        state: Shared state dict
        data_source: RdmDataSource (typically a Store)
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
        data_source: RdmDataSource,
        config: TableConfig,
        filter_by: dict[str, Any] | None = None,
        action_style: Literal["icon", "button"] = "icon",
        on_edit: Callable[[dict], Awaitable[None] | None] | None = None,
        on_delete: Callable[[dict], Awaitable[None] | None] | None = None,
        edit_label: str | None = None,
        delete_label: str | None = None,
        auto_observe: bool = True,
    ):
        super().__init__(state, data_source)
        self.config = config
        self.filter_by = filter_by
        self.action_style = action_style
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.edit_label = edit_label or _("Edit")
        self.delete_label = delete_label or _("Delete")
        self.dialog_state: dict[str, Any] = {}
        self._current_item_id: int | None = None
        self._dlg: Dialog | None = None
        self._dialog_content: Any = None
        self._is_edit: bool = False
        if auto_observe:
            self.observe(topics=filter_by)

    async def load_data(
        self,
        join_fields: list[str] | None = None,
        filter_by: dict[str, Any] | None = None,
        transform: Callable[[list[dict]], list[dict]] | None = None,
    ):
        """Load data from store with filter and join fields from config."""
        await super().load_data(
            join_fields=join_fields or self.config.join_fields,
            filter_by=filter_by if filter_by is not None else self.filter_by,
            transform=transform,
        )

    @ui.refreshable_method
    async def build(self):
        """Build the table using native HTML elements."""
        await self.load_data()

        with html.div().classes("rdm-table-card rdm-component show-refresh"):
            with html.table().classes("rdm-table"):
                # Header
                with html.thead():
                    with html.tr():
                        for col in self.config.table_columns:
                            th = html.th(col.label or col.name)
                            if col.width_percent:
                                th.style(f"width: {col.width_percent}%")
                        # Actions column header
                        if self.config.show_edit_button or self.config.show_delete_button:
                            html.th("").classes("rdm-col-actions")

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
                                ).classes("rdm-text-muted")
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
                with html.td().classes("rdm-col-actions"):
                    with html.div().classes("rdm-actions"):
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
            btn = html.button().classes("rdm-btn rdm-btn-icon").on(
                "click", lambda _, r=row, a=action: self._handle_custom_action(a, r)
            )
            with btn:
                html.i().classes(f"bi bi-{action.icon}")
            if action.tooltip:
                btn.props(f'title="{action.tooltip}"')
        elif effective_style in ("primary", "secondary", "danger") and action.label:
            # Explicit variant with label
            btn_class = f"rdm-btn rdm-btn-{effective_style} rdm-btn-sm"
            with html.button().classes(btn_class).on(
                "click", lambda _, r=row, a=action: self._handle_custom_action(a, r)
            ):
                html.span(action.label)
        elif effective_style == "button" and action.label:
            # Generic button style - default to primary
            with html.button().classes("rdm-btn rdm-btn-primary rdm-btn-sm").on(
                "click", lambda _, r=row, a=action: self._handle_custom_action(a, r)
            ):
                html.span(action.label)
        elif action.label:
            # Fallback: have label but no matching style, render as primary button
            with html.button().classes("rdm-btn rdm-btn-primary rdm-btn-sm").on(
                "click", lambda _, r=row, a=action: self._handle_custom_action(a, r)
            ):
                html.span(action.label)
        elif action.icon:
            # Fallback: have icon but button style requested, render as icon anyway
            btn = html.button().classes("rdm-btn rdm-btn-icon").on(
                "click", lambda _, r=row, a=action: self._handle_custom_action(a, r)
            )
            with btn:
                html.i().classes(f"bi bi-{action.icon}")
            if action.tooltip:
                btn.props(f'title="{action.tooltip}"')

    def _render_edit_button(self, row: dict):
        """Render edit button based on action_style."""
        if self.action_style == "icon":
            with html.button().classes("rdm-btn rdm-btn-icon").on(
                "click", lambda _, r=row: self._handle_edit(r)
            ):
                html.i().classes("bi bi-pencil")
        else:
            with html.button().classes("rdm-btn rdm-btn-primary rdm-btn-sm").on(
                "click", lambda _, r=row: self._handle_edit(r)
            ):
                html.span(self.edit_label)

    def _render_delete_button(self, row: dict):
        """Render delete button based on action_style."""
        if self.action_style == "icon":
            with html.button().classes("rdm-btn rdm-btn-icon").on(
                "click", lambda _, r=row: self._handle_delete(r)
            ):
                html.i().classes("bi bi-trash")
        else:
            with html.button().classes("rdm-btn rdm-btn-secondary rdm-btn-sm").on(
                "click", lambda _, r=row: self._handle_delete(r)
            ):
                html.span(self.delete_label)

    def render_add_button(self):
        """Render the add button - call from page code to position alongside other buttons."""
        if self.config.add_button and self.config.show_add_button:
            with html.button().classes("rdm-btn rdm-btn-primary").on(
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

    def _open_add_dialog(self):
        """Open dialog for adding new item."""
        self.dialog_state = self._init_form_state(self.config.dialog_columns)
        self._current_item_id = None
        self._is_edit = False
        self._show_dialog()

    def _open_edit_dialog(self, item: dict):
        """Open dialog for editing existing item."""
        self.dialog_state = self._init_form_state(self.config.dialog_columns, item)
        self._current_item_id = item.get("id")
        self._is_edit = True
        self._show_dialog()

    def _show_dialog(self):
        """Show the modal dialog, creating it lazily on first use."""
        if self._dlg is None:
            self._build_dialog()
        else:
            self._dialog_content.refresh()
        assert self._dlg is not None
        self._dlg.open()

    def _build_dialog(self):
        """Build the dialog structure once."""
        dialog_class = self.config.dialog_class or ""
        with Dialog(dialog_class=dialog_class) as self._dlg:
            @ui.refreshable
            def _content():
                title = (
                    self.config.dialog_title_edit if self._is_edit else self.config.dialog_title_add
                ) or (_("Edit") if self._is_edit else _("Add"))
                assert self._dlg is not None

                # Header
                with html.div().classes("rdm-dialog-header"):
                    ui.label(title).classes("rdm-dialog-title")
                    with html.button().classes("rdm-dialog-close").on("click", self._dlg.close):
                        html.i().classes("bi bi-x-lg")

                # Form fields
                for col in self.config.dialog_columns:
                    build_form_field(col, self.dialog_state)

            self._dialog_content = _content
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

    async def _handle_save(self):
        """Handle save button click in dialog."""
        item_data = self._build_item_data(self.config.dialog_columns, self.dialog_state)

        # Validate
        (valid, error_dict) = self._validate(item_data)
        if not valid:
            return

        if self._is_edit and self._current_item_id is not None:
            success = await self._update(self._current_item_id, item_data)
        else:
            success = await self._validate_and_create(item_data)

        if success and self._dlg:
            self._dlg.close()
