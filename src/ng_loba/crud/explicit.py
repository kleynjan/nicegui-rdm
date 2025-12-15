"""
Explicit edit CRUD table - row selection with dedicated edit mode.
"""

import time
from typing import Any, Callable

from nicegui import html, ui

from .base import CLASSES_PREFIX, BaseCrudTable, TableConfig
from .protocol import CrudDataSource


class TableRowEditor:
    """Editor for a single table row"""
    def __init__(self, table: 'ExplicitEditTable', state: dict, data_source: CrudDataSource, config: TableConfig):
        self.table = table
        self.state = state
        self.data_source = data_source
        self.config = config
        self.old_item = {}
        self.elements = {}

    def build(self, item: dict):
        """Build the editor UI"""
        self.item = item
        self.old_item = item.copy()
        self.check_validity()
        if not self.state['current_col']:
            self.state['current_col'] = self.config.focus_column

        with html.tr().classes(f"{CLASSES_PREFIX}-row-tr"):
            for col in self.config.columns:
                col_name = col.name
                if col.ui_type:
                    cls = col.ui_type
                    cls_parms = col.parms.copy()
                    cls_parms["value"] = item[col_name]
                    cls_parms["validation"] = self._validation_function_factory(col_name)
                    props = col.props
                    with html.td().classes(f"{CLASSES_PREFIX}-td {CLASSES_PREFIX}-td-{col_name}"):
                        el = (
                            cls(**cls_parms)
                            .classes(f"{CLASSES_PREFIX}-input {CLASSES_PREFIX}-input-{col_name}")
                            .bind_value(item, col_name)
                        )
                        el.props(props)
                        el.on('keydown', self.handle_key)
                        self._register_element(el, col_name)

            with html.td().classes(f"{CLASSES_PREFIX}-td-button"):
                el = ui.button(icon='bi-check-square').classes(f"{CLASSES_PREFIX}-column-button positive").props('flat')
                el.on("click", self.handle_save).bind_enabled_from(self.state, "is_valid")
                self._register_element(el, 'save_button')
            with html.td().classes(f"{CLASSES_PREFIX}-td-button"):
                el = ui.button(icon='bi-x-square').classes(f"{CLASSES_PREFIX}-column-button negative").props('flat')
                el.on('click', self.handle_cancel)
                self._register_element(el, 'cancel_button')

        self.set_focus(self.state['current_col'])

    def _validation_function_factory(self, col_name: str) -> Callable:
        """Create a nicegui/quasar compatible validation function for a given column."""
        def _validate(value: Any):
            partial = {col_name: value}
            (valid, error_dict) = self.data_source.validate(partial)
            # always validate entire row -> enable/disable save button
            self.check_validity()
            return None if valid else error_dict['error_msg']
        return _validate

    def _register_element(self, element, col_name):
        """Register an element for focus management"""
        self.elements[col_name] = element

    def set_focus(self, col_name):
        """Move to given field and if possible, select current content."""
        if el := self.elements.get(col_name):
            el.run_method('focus')
            if self.config.find_column(col_name):
                el.run_method('select')

    def check_validity(self) -> bool:
        """Check validity of entire current row"""
        (valid_all, error_dict) = self.data_source.validate(self.item)
        self.state['is_valid'] = valid_all
        if valid_all:
            self.state['current_error'] = {}
        return valid_all

    async def handle_save(self):
        """Handle save button click"""
        if self.check_validity():
            if self.item['id'] == -1:
                # Create new item - remove the temporary id
                item_data = {k: v for k, v in self.item.items() if k != 'id'}
                await self.data_source.create_item(item_data)
                self.table._notify("Item added", type='positive')
                # Exit edit mode after save
                self.table.exit_editing()
            elif self.item != self.old_item:
                # Update existing item - pass only changed fields (or all fields except id)
                item_id = self.item['id']
                item_data = {k: v for k, v in self.item.items() if k != 'id'}
                await self.data_source.update_item(item_id, item_data)
                self.table._notify("Item updated", type='positive')
                # Exit edit mode after save
                self.table.exit_editing()
            else:
                self.table._notify("No changes", type='info')
                self.table.exit_editing()

    def handle_cancel(self):
        """Handle cancel button click"""
        self.item.update(self.old_item)
        self.table.exit_editing()

    async def handle_key(self, e):
        """Handle keyboard events in editor"""
        key = e.args.get('key')
        if key == 'Escape':
            self.handle_cancel()
        elif key == 'Enter':
            # Save on Enter (if valid)
            if self.state['is_valid']:
                await self.handle_save()


class ExplicitEditTable(BaseCrudTable):
    """Explicit edit mode - row selection with dedicated edit mode"""

    def __init__(self, state: dict, data_source: CrudDataSource, config: TableConfig):
        super().__init__(state, data_source, config)
        self.reset()
        self.state['selected_row'] = None
        self.editor = TableRowEditor(table=self, state=self.state['editor'], data_source=data_source,
                                     config=config)
        self.keyboard = ui.keyboard(on_key=self.handle_key)

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
        self.last_click_time = 0  # Track last click time for double-click detection

    def _build_header_buttons(self):
        """Add button column headers"""
        with html.th().classes(f"{CLASSES_PREFIX}-th-button"):
            ui.label("")
        with html.th().classes(f"{CLASSES_PREFIX}-th-button"):
            ui.label("")

    @ui.refreshable
    async def build(self):
        """Build the table UI"""
        await self.load_data()
        with html.table().classes(f"{CLASSES_PREFIX}-table {CLASSES_PREFIX}-explicit-mode show-refresh"):
            self._build_header()
            self._build_body()  # type: ignore

    @ui.refreshable
    def _build_body(self):
        """Build table body"""
        if not self.data:
            print("No data to display")
            return

        with html.tbody().classes(f"{CLASSES_PREFIX}-tbody"):
            for row_index, row in enumerate(self.data):
                if row_index == self.state['selected_row'] and self.state['is_editing']:
                    self.editor.build(row)
                else:
                    with html.tr().classes(f"{CLASSES_PREFIX}-row-tr") as row_element:
                        for col in self.config.columns:
                            col_name = col.name
                            with html.td().classes(f"{CLASSES_PREFIX}-td {CLASSES_PREFIX}-td-{col_name}"):
                                ui.label(row[col_name]).on("click", lambda _, r=row_index,
                                                           c=col_name: self.row_click(r, c))
                        if row_index == self.state["selected_row"]:
                            row_element.classes(add="selected")
                            with html.td().classes(f"{CLASSES_PREFIX}-td-button"):
                                ui.button(icon="bi-pencil").classes(f"{CLASSES_PREFIX}-column-button").props('flat') \
                                    .on("click", lambda _, r=row_index: self.start_editing(r, self.config.focus_column or self.config.columns[0].name))
                            if not self.config.skip_delete:
                                with html.td().classes(f"{CLASSES_PREFIX}-td-button"):
                                    ui.button(icon="bi-trash").classes(f"{CLASSES_PREFIX}-column-button").props('flat') \
                                        .on("click", lambda _, r=row_index: self._handle_delete(r))

            if self.state['adding_new_item']:
                self.editor.build(item=self.new_item)

        if not self.state['adding_new_item']:
            with html.tr().classes(f"{CLASSES_PREFIX}-add-button-row"):
                with html.td().props(f"colspan={len(self.config.columns)}"):
                    btn_text = self.config.add_button or "Add new"
                    ui.button(btn_text).classes(f"{CLASSES_PREFIX}-button {CLASSES_PREFIX}-add-button").props('flat') \
                        .on('click', self.start_new_row)

                    if (row_index := self.state['selected_row']) is not None:
                        btn_text = "Delete"
                        ui.button(btn_text).classes(f"{CLASSES_PREFIX}-button {CLASSES_PREFIX}-delete-button").props('flat') \
                            .on('click', lambda _, r=row_index: self._handle_delete(r))

    def row_click(self, row_index: int, col_name: str) -> None:
        """Handle row click"""
        if self.state['is_editing']:
            return
        old_time = self.last_click_time
        current_time = time.time()
        self.last_click_time = current_time

        # Check if this is a double-click (within 500ms)
        if (current_time - old_time < 0.5 and
                self.state['selected_row'] == row_index):
            # Double-click detected, start editing
            self.start_editing(row_index, col_name)
        else:
            # Single click, just select the row
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
        # _delete checks config.delete_confirmation automatically and refreshes
        await self._delete(item)

    def handle_key(self, e):
        """Handle keyboard events at table level"""
        # Only handle table-level keys when NOT editing
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
                if not self.state['is_editing']:  # Only navigate when not editing
                    delta = 1 if e.key.name == 'ArrowDown' else -1
                    ssr = self.state['selected_row']
                    if ssr is None:
                        ssr = -1
                    ssr = min(max(ssr + delta, 0), len(self.data) - 1)
                    self.state['selected_row'] = ssr
                    self._build_body.refresh()  # type: ignore
