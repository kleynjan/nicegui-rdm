"""
Explicit edit CRUD table - row selection with dedicated edit mode.
Uses div-based flexbox layout with crudy-* classes.
"""

import time
from typing import Any, Awaitable, Callable

from nicegui import ui

from .base import TableConfig
from ._table_base import BaseCrudTable
from .protocol import CrudDataSource


class ExplicitEditTable(BaseCrudTable):
    """Explicit edit mode - row selection with dedicated edit mode.

    Supports:
    - Per-column on_click: callback for navigation (set on Column)
    - row_key: field to use as row identifier (default "id")
    - editable per column: non-editable columns display as labels even in edit mode
    """

    def __init__(
        self,
        state: dict,
        data_source: CrudDataSource,
        config: TableConfig,
        row_key: str = "id",
        filter_by: dict[str, Any] | None = None,
    ):
        super().__init__(state, data_source, config)
        self.row_key = row_key
        self.filter_by = filter_by
        self.reset()
        self.state['selected_row'] = None
        self.keyboard = ui.keyboard(on_key=self.handle_key)
        # row editor state
        self.edit_elements = {}
        self.current_item = {}
        self.old_item = {}

    async def load_data(self):
        """Load data from store with filter and join fields from config."""
        self.data = await self.data_source.read_items(
            filter_by=self.filter_by,
            join_fields=self.config.join_fields,
        )

    def reset(self):
        """Reset table state"""
        self.state.update({
            'is_editing': False,
            "current_error": {},
            "adding_new_item": False,
            'editor': {'is_valid': False, 'current_col': self.config.focus_column}
        })
        self.new_item = {col.name: col.default_value for col in self.config.columns}
        self.new_item['id'] = -1
        self.last_click_time = 0
        self.edit_elements = {}
        self.current_item = {}
        self.old_item = {}

    def _build_header(self):
        """Build header row using divs with flexbox pattern"""
        with ui.row().classes("crudy-header"):
            for column in self.config.columns:
                ui.label(column.label or column.name).classes(f"crudy-col-{column.name}").style(column.width_style)
            # Empty header for actions column - no width_style, fills remaining space
            ui.label("").classes("crudy-col-actions")

    @ui.refreshable
    async def build(self):
        """Build the table UI"""
        await self.load_data()
        with ui.card().classes("crudy-card crudy-explicit-mode"):
            self._build_header()
            self._build_body()  # type: ignore

    @ui.refreshable
    def _build_body(self):
        """Build table body"""
        if not self.data:
            with ui.row().classes("crudy-row"):
                ui.label("No data to display").classes("text-muted")
            return

        for row_index, row in enumerate(self.data):
            if row_index == self.state['selected_row'] and self.state['is_editing']:
                self._build_edit_row(row)
            else:
                self._build_view_row(row_index, row)

        if self.state['adding_new_item']:
            self._build_edit_row(item=self.new_item)

        # Add button row
        if not self.state['adding_new_item'] and self.config.show_add_button:
            with ui.row().classes("crudy-add-row"):
                btn_text = self.config.add_button or "Add new"
                ui.label(btn_text) \
                    .on("click", self.start_new_row) \
                    .classes("crudy-add-button")

    def _build_view_row(self, row_index: int, row: dict):
        """Build a view-only row (not editing)"""
        is_selected = row_index == self.state["selected_row"]
        row_classes = "crudy-row selected" if is_selected else "crudy-row"

        with ui.row().classes(row_classes):
            # Data columns - labels
            for col in self.config.columns:
                col_name = col.name
                with ui.element("div").classes(f"crudy-col-{col_name}").style(col.width_style):
                    if col.render:
                        col.render(row)
                    elif col.on_click:
                        raw_value = row.get(col_name, "")
                        display = col.formatter(raw_value) if col.formatter else str(raw_value)
                        ui.label(display).classes("crudy-link").on(
                            "click", lambda _, r=row, c=col: c.on_click(r)  # type: ignore
                        )
                    else:
                        raw_value = row.get(col_name, "")
                        display = col.formatter(raw_value) if col.formatter else str(raw_value)
                        ui.label(display).on(
                            "click", lambda _, r=row_index, c=col_name: self.row_click(r, c)
                        )

            # Action buttons (only show for selected row)
            with ui.element("div").classes("crudy-col-actions"):
                if is_selected:
                    # Only show edit button if there are editable columns
                    has_editable = any(c.editable and c.ui_type for c in self.config.columns)
                    if has_editable:
                        ui.button(icon="bi-pencil",
                                  on_click=lambda _, r=row_index: self.start_editing(
                                      r, self.config.focus_column or self.config.columns[0].name)) \
                            .props("flat dense size=md").classes("crudy-btn-icon")
                    if self.config.show_delete_button:
                        ui.button(icon="bi-trash",
                                  on_click=lambda _, r=row_index: self._handle_delete(r)) \
                            .props("flat dense size=md").classes("crudy-btn-icon")

    def _build_edit_row(self, item: dict):
        """Build the editor UI for a single row"""
        self.current_item = item
        self.old_item = item.copy()
        self._check_validity()
        if not self.state['editor']['current_col']:
            self.state['editor']['current_col'] = self.config.focus_column

        with ui.row().classes("crudy-row crudy-editing"):
            for col in self.config.columns:
                col_name = col.name
                with ui.element("div").classes(f"crudy-col-{col_name}").style(col.width_style):
                    # Non-editable columns: display as label even in edit mode
                    if not col.editable or not col.ui_type:
                        ui.label(str(item.get(col_name, "")))
                    else:
                        # Editable columns: render input
                        cls = col.ui_type
                        cls_parms = col.parms.copy()
                        cls_parms["value"] = item.get(col_name, col.default_value)
                        cls_parms["validation"] = self._validation_function_factory(col_name)
                        props = col.props or ""

                        el = cls(**cls_parms).classes("crudy-input").bind_value(item, col_name)
                        combined_props = f"dense flat {props}".strip()
                        el.props(combined_props)
                        el.on('keydown', self._handle_editor_key)
                        self._register_element(el, col_name)

            # Save/Cancel buttons
            with ui.element("div").classes("crudy-col-actions"):
                ui.button(icon="bi-check-square",
                          on_click=self._handle_editor_save) \
                    .props("flat dense size=md").classes("crudy-btn-icon") \
                    .bind_enabled_from(self.state['editor'], "is_valid")
                ui.button(icon="bi-x-square",
                          on_click=self._handle_editor_cancel) \
                    .props("flat dense size=md").classes("crudy-btn-icon")

        self._set_focus(self.state['editor']['current_col'])

    # ============= Private Editor Methods =============

    def _validation_function_factory(self, col_name: str) -> Callable:
        """Create a nicegui/quasar compatible validation function for a given column."""
        def _validate(value: Any):
            partial = {col_name: value}
            (valid, error_dict) = self.data_source.validate(partial)
            self._check_validity()
            return None if valid else error_dict['error_msg']
        return _validate

    def _register_element(self, element, col_name):
        """Register an element for focus management"""
        self.edit_elements[col_name] = element

    def _set_focus(self, col_name):
        """Move to given field and if possible, select current content."""
        if el := self.edit_elements.get(col_name):
            el.run_method('focus')
            if self.config.find_column(col_name):
                el.run_method('select')

    def _check_validity(self) -> bool:
        """Check validity of entire current row"""
        (valid_all, error_dict) = self.data_source.validate(self.current_item)
        self.state['editor']['is_valid'] = valid_all
        if valid_all:
            self.state['current_error'] = {}
        return valid_all

    async def _handle_editor_save(self):
        """Handle save button click"""
        if self._check_validity():
            if self.current_item['id'] == -1:
                item_data = {k: v for k, v in self.current_item.items() if k != 'id'}
                success = await self._validate_and_create(item_data)
                if success:
                    self.exit_editing()
            elif self.current_item != self.old_item:
                item_id = self.current_item['id']
                item_data = {k: v for k, v in self.current_item.items() if k != 'id'}
                success = await self._update(item_id, item_data)
                if success:
                    self.exit_editing()
            else:
                self._notify("No changes", type='info')
                self.exit_editing()

    def _handle_editor_cancel(self):
        """Handle cancel button click"""
        self.current_item.update(self.old_item)
        self.exit_editing()

    async def _handle_editor_key(self, e):
        """Handle keyboard events in editor"""
        key = e.args.get('key')
        if key == 'Escape':
            self._handle_editor_cancel()
        elif key == 'Enter':
            if self.state['editor']['is_valid']:
                await self._handle_editor_save()

    # ============= Public Table Methods =============

    def row_click(self, row_index: int, col_name: str) -> None:
        """Handle row click"""
        if self.state['is_editing']:
            return
        old_time = self.last_click_time
        current_time = time.time()
        self.last_click_time = current_time

        if (current_time - old_time < 0.5 and
                self.state['selected_row'] == row_index):
            self.start_editing(row_index, col_name)
        else:
            self.select_row(row_index)

    def start_editing(self, row_index: int, col_name: str) -> None:
        """Start editing a row"""
        self.state['editor']['current_col'] = col_name
        self.state['is_editing'] = True
        self._build_body.refresh()  # type: ignore

    def start_new_row(self):
        """Start adding a new row"""
        self.state['adding_new_item'] = True
        self.state['selected_row'] = None
        self._build_body.refresh()  # type: ignore

    def exit_editing(self):
        self.reset()
        self._build_body.refresh()  # type: ignore

    def select_row(self, row_index: int) -> None:
        """Select a row"""
        if not self.state['is_editing']:
            self.state['selected_row'] = row_index
            self._build_body.refresh()  # type: ignore

    async def _handle_delete(self, row_index):
        """Handle row deletion - respects config.delete_confirmation"""
        item = self.data[row_index]
        await self._delete(item)

    def handle_key(self, e):
        """Handle keyboard events at table level"""
        if self.state['is_editing']:
            return

        if e.action.keydown:
            if e.key.name == 'Escape':
                self.state['selected_row'] = None
                self._build_body.refresh()
            elif e.key.name == 'Enter':
                selected_row = self.state['selected_row']
                if selected_row is not None:
                    focus_col = self.config.focus_column or self.config.columns[0].name
                    self.start_editing(selected_row, focus_col)
            elif e.key.name in ['ArrowDown', 'ArrowUp']:
                if not self.state['is_editing']:
                    delta = 1 if e.key.name == 'ArrowDown' else -1
                    ssr = self.state['selected_row']
                    if ssr is None:
                        ssr = -1
                    ssr = min(max(ssr + delta, 0), len(self.data) - 1)
                    self.state['selected_row'] = ssr
                    self._build_body.refresh()  # type: ignore
