"""
ActionButtonTable - Table with action buttons per row.

Uses native HTML <table> elements for clean, semantic markup.
Supports both icon and button styles for Edit/Delete/custom actions.
All action semantics delegated to client callbacks.
"""
from typing import Any, Awaitable, Callable, Literal

from nicegui import html, ui

from .i18n import _
from .base import ObservableRdmTable, TableConfig
from .protocol import RdmDataSource


class ActionButtonTable(ObservableRdmTable):
    """Table with action buttons per row.

    Uses native HTML table elements with rdm-* CSS classes.
    Supports icon or button styles for actions.
    All action semantics (edit, delete, custom) are handled via callbacks.

    Args:
        state: Shared state dict
        data_source: RdmDataSource (typically a Store)
        config: TableConfig with column definitions
        filter_by: Optional filter dict for data loading
        action_style: "icon" for icon buttons, "button" for text buttons
        on_add: Callback when Add button clicked
        on_edit: Callback when Edit button clicked, receives row dict
        on_delete: Callback when Delete button clicked, receives row dict
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
        on_add: Callable[[], Awaitable[None] | None] | None = None,
        on_edit: Callable[[dict], Awaitable[None] | None] | None = None,
        on_delete: Callable[[dict], Awaitable[None] | None] | None = None,
        edit_label: str | None = None,
        delete_label: str | None = None,
        render_toolbar: Callable[[], None] | None = None,
        auto_observe: bool = True,
    ):
        super().__init__(
            state, data_source, config,
            filter_by=filter_by, on_add=on_add,
            render_toolbar=render_toolbar, auto_observe=auto_observe,
        )
        self.action_style = action_style
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.edit_label = edit_label or _("Edit")
        self.delete_label = delete_label or _("Delete")

    @ui.refreshable_method
    async def build(self):
        """Build the table using native HTML elements."""
        await self.load_data()
        self._build_toolbar("top")

        with html.div().classes("rdm-table-card rdm-component show-refresh"):
            with html.table().classes("rdm-table"):
                # Header
                with html.thead():
                    with html.tr():
                        for col in self.config.columns:
                            th = html.th(col.label or col.name)
                            if col.width_percent:
                                th.style(f"width: {col.width_percent}%")
                        # Actions column header
                        if self.config.show_edit_button or self.config.show_delete_button or self.config.custom_actions:
                            html.th("").classes("rdm-col-actions")

                # Body
                with html.tbody():
                    if not self.data:
                        with html.tr():
                            colspan = len(self.config.columns)
                            if self.config.show_edit_button or self.config.show_delete_button or self.config.custom_actions:
                                colspan += 1
                            with html.td().props(f"colspan={colspan}"):
                                html.span(
                                    self.config.empty_message or _("No data")
                                ).classes("rdm-text-muted")
                    else:
                        for row in self.data:
                            self._build_row(row)

        self._build_toolbar("bottom")

    def _build_row(self, row: dict):
        """Build a single data row."""
        with html.tr():
            # Data columns
            for col in self.config.columns:
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

    async def _handle_custom_action(self, action, row: dict):
        """Handle custom action button click."""
        if action.callback:
            result = action.callback(row)
            if hasattr(result, '__await__'):
                await result

    async def _handle_edit(self, row: dict):
        """Handle edit button click."""
        if self.on_edit:
            result = self.on_edit(row)
            if result is not None and hasattr(result, '__await__'):
                await result

    async def _handle_delete(self, row: dict):
        """Handle delete button click."""
        if self.on_delete:
            result = self.on_delete(row)
            if result is not None and hasattr(result, '__await__'):
                await result
