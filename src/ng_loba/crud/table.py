"""
CRUD table component for data management.
"""

from dataclasses import dataclass, field
import time
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional

from nicegui import html, ui

from ..utils.keyboard import ObservableKeyboard
from ..store.base import Store

CLASSES_PREFIX = "crudy"

@dataclass
class Column:
    """Configuration for a table column"""
    name: str
    label: Optional[str] = None
    ui_type: Optional[Any] = None
    default_value: Any = ""
    parms: Dict[str, Any] = field(default_factory=dict)      # passed to the ui_type instance
    props: Optional[str] = ""                                # passed to el.props()

@dataclass
class TableConfig:
    """Configuration for CrudTable"""
    columns: List[Column]
    focus_column: str                   # default column to set focus to for editor
    on_add: Optional[Callable] = None   # note, if provided, this must create item
    skip_delete: bool = False
    add_button: Optional[str] = None

    def __post_init__(self):
        self.join_fields = [col.name for col in self.columns if "__" in col.name]
        if not self.focus_column and self.columns:
            self.focus_column = self.columns[0].name

    def find_column(self, col_name: str) -> Optional[Column]:
        """Find column by name"""
        for col in self.columns:
            if col.name == col_name:
                return col
        return None


async def confirm_dialog(prompts: dict = {}, item: dict = {}):
    """Show a confirmation dialog"""
    dialog = ui.dialog().props('persistent').classes('confirm-dialog')

    question = prompts.get('question', 'Are you sure?').format(**item)
    explanation = prompts.get('explanation', '').format(**item)
    yes_button = prompts.get('yes_button', 'Yes').format(**item)
    no_button = prompts.get('no_button', 'No').format(**item)

    with dialog as d, ui.card().classes('delete-card'):
        ui.label(question).classes('question')
        ui.label(explanation).classes('explanation')
        with ui.row().classes('confirm-button-row'):
            ui.button(no_button).on("click", lambda: d.submit(False)) \
                .classes("confirm-button confirm-button-no")
            ui.button(yes_button).on("click", lambda: d.submit(True)) \
                .classes("confirm-button confirm-button-yes")

    result = await dialog
    return result


class TableRowEditor:
    """Editor for a single table row"""
    def __init__(self, state: dict, store: Store, config: TableConfig, on_ready: Callable):
        self.state = state
        self.store = store
        self.config = config
        self.on_ready = on_ready
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
                el = ui.button(icon='bi-check-square').classes(f"{CLASSES_PREFIX}-column-button positive")
                el.on("click", self.handle_save).bind_enabled_from(self.state, "is_valid")
                self._register_element(el, 'save_button')
            with html.td().classes(f"{CLASSES_PREFIX}-td-button"):
                el = ui.button(icon='bi-x-square').classes(f"{CLASSES_PREFIX}-column-button negative")
                el.on('click', self.handle_cancel)
                self._register_element(el, 'cancel_button')

        self.set_focus(self.state['current_col'])

    def _validation_function_factory(self, col_name: str) -> Callable:
        """Create a nicegui/quasar compatible validation function for a given column."""
        def _validate(value: Any):
            partial = {col_name: value}
            # if col.ui_type == ui.checkbox:      # type: ignore
            #     partial = {col_name: not partial[col_name]}
            #     print(f"Checkbox partial: {partial}")
            (valid, error_dict) = self.store.validate(partial)
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
        (valid_all, error_dict) = self.store.validate(self.item)
        self.state['is_valid'] = valid_all
        if valid_all:
            self.state['current_error'] = {}
        return valid_all

    async def handle_save(self):
        """Handle save button click"""
        if self.check_validity():
            if self.item['id'] == -1:
                self.item.pop('id')
                await self.store.create_item(self.item)
                ui.notify("Item added", type='positive')
            elif self.item != self.old_item:
                await self.store.update_item(self.item['id'], self.item)
                ui.notify("Item updated", type='positive')
            else:
                ui.notify("No changes", type='info')
            self.on_ready()

    def handle_cancel(self):
        """Handle cancel button click"""
        self.item.update(self.old_item)
        self.on_ready()

    def handle_key(self, e):
        """Handle keyboard events"""
        key = e.args.get('key')
        if key == 'Escape':
            self.handle_cancel()


class CrudTable:
    """CRUD table component"""
    def __init__(self, state: dict, store: Store, config: TableConfig):
        self.store: Store = store
        self.state = state
        self.config: TableConfig = config
        self.data: List[Dict[str, Any]] = []
        self.reset()
        self.state['selected_row'] = None
        self.editor = TableRowEditor(state=self.state['editor'], store=store,
                                     config=config, on_ready=self.handle_editor_ready)
        self.keyboard = ObservableKeyboard()
        self.keyboard.add_observer(self.handle_key)

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

    @ui.refreshable
    async def build(self):
        """Build the table UI"""
        self.data = await self.store.read_items(join_fields=self.config.join_fields)
        with html.table().classes(f"{CLASSES_PREFIX}-table show-refresh"):
            self._build_header()
            self._build_body()  # type: ignore

    def _build_header(self):
        """Build table header"""
        with html.tr().classes(f"{CLASSES_PREFIX}-header-tr"):
            for column in self.config.columns:
                with html.th().classes(f"{CLASSES_PREFIX}-th {CLASSES_PREFIX}-th-{column.name}"):
                    ui.label(column.label or column.name)
            with html.th().classes(f"{CLASSES_PREFIX}-th-button"):
                ui.label("")
            with html.th().classes(f"{CLASSES_PREFIX}-th-button"):
                ui.label("")

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
                                ui.button(icon="bi-pencil").classes(f"{CLASSES_PREFIX}-column-button") \
                                    .on("click", lambda e, r=row_index, c=col_name: self.start_editing(r, c))
                            if not self.config.skip_delete:
                                with html.td().classes(f"{CLASSES_PREFIX}-td-button"):
                                    ui.button(icon="bi-trash").classes(f"{CLASSES_PREFIX}-column-button") \
                                        .on("click", lambda e, r=row_index: self._handle_delete(r))

            if self.state['adding_new_item']:
                self.editor.build(item=self.new_item)

        if not self.state['adding_new_item']:
            with html.tr().classes(f"{CLASSES_PREFIX}-add-button-row"):
                with html.td().props(f"colspan={len(self.config.columns)}"):
                    btn_text = self.config.add_button or "Add new"
                    ui.button(btn_text).on('click', self.start_new_row).classes(
                        f"{CLASSES_PREFIX}-button {CLASSES_PREFIX}-add-button")

                    if (row_index := self.state['selected_row']) is not None:
                        btn_text = "Delete"
                        ui.button(btn_text).on('click', lambda _, r=row_index: self._handle_delete(r)).classes(
                            f"{CLASSES_PREFIX}-button {CLASSES_PREFIX}-delete-button")

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
        self._build_body.refresh()

    def start_new_row(self):
        """Start adding a new row"""
        self.state['adding_new_item'] = True
        self.state['selected_row'] = None
        self._build_body.refresh()

    def handle_editor_ready(self):
        """Handle editor completion"""
        self.reset()
        self._build_body.refresh()

    def select_row(self, row_index: int) -> None:
        """Select a row"""
        if not self.state['is_editing']:
            self.state['selected_row'] = row_index
            self._build_body.refresh()

    async def _handle_delete(self, row_index):
        """Handle row deletion"""
        item = self.data[row_index]
        if await confirm_dialog({
            'question': 'Delete item?',
            'explanation': 'This action cannot be undone',
            'no_button': 'Cancel',
            'yes_button': 'Delete'
        }, item):
            await self.store.delete_item(item)

    def handle_key(self, e):
        """Handle keyboard events"""
        if e.action.keydown:
            if e.key.name == 'Escape':
                if self.state['is_editing']:
                    self.handle_editor_ready()
                else:
                    self.state['selected_row'] = None
                    self._build_body.refresh()
            if e.key.name == 'Enter':
                selected_row = self.state['selected_row']
                if selected_row is not None:
                    self.start_editing(selected_row, self.config.focus_column)
            if e.key.name in ['ArrowDown', 'ArrowUp']:
                delta = 1 if e.key.name == 'ArrowDown' else -1
                ssr = self.state['selected_row']
                if ssr is None:
                    ssr = -1
                ssr = min(max(ssr + delta, 0), len(self.data) - 1)
                self.state['selected_row'] = ssr
                self._build_body.refresh()
