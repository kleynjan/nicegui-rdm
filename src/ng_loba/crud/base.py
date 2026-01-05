"""
Base class for CRUD table implementations.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from nicegui import html, ui

from .protocol import CrudDataSource
from ..store.base import StoreEvent

CLASSES_PREFIX = "crudy"

@dataclass
class Column:
    """Configuration for a table column"""
    name: str
    label: Optional[str] = None
    ui_type: Optional[Any] = None
    default_value: Any = ""
    parms: dict[str, Any] = field(default_factory=dict)      # passed to the ui_type instance
    props: Optional[str] = ""                                # passed to el.props()
    width_percent: Optional[float] = None                    # column width as percentage (0-100)

@dataclass
class TableConfig:
    """Configuration for CrudTable"""
    columns: list[Column]
    mode: str = "explicit"              # "explicit" or "direct"
    skip_delete: bool = False           # Hide delete functionality
    add_button: Optional[str] = None    # Custom add button text
    focus_column: Optional[str] = None  # Default column for focus (explicit mode)
    delete_confirmation: bool = True    # Confirm deletes (explicit mode)

    def __post_init__(self):
        self.join_fields = [col.name for col in self.columns if "__" in col.name]
        if not self.focus_column and self.columns:
            self.focus_column = self.columns[0].name

    def find_column(self, col_name: str) -> Column | None:
        """Find column by name"""
        for col in self.columns:
            if col.name == col_name:
                return col
        return None


class BaseCrudTable:
    """Base class for CRUD table implementations"""

    def __init__(self, state: dict, data_source: CrudDataSource, config: TableConfig):
        self.data_source = data_source
        self.state = state
        self.config = config
        self.data: list[dict[str, Any]] = []
        # capture client context for notifications
        self._client = ui.context.client
        # subscribe to data source changes - required to refresh table on data updates
        data_source.add_observer(self._handle_datasource_change)

    async def load_data(self):
        """Load data from data source"""
        self.data = await self.data_source.read_items(
            join_fields=self.config.join_fields
        )

    async def _handle_datasource_change(self, event: StoreEvent):
        """Handle data source changes (create/update/delete operations)"""
        # Refresh the table to show the changes - this is the core of the observer pattern
        await self.build.refresh()  # type: ignore

    def _build_header(self):
        """Build table header - common to both modes"""
        with html.tr().classes(f"{CLASSES_PREFIX}-header-tr"):
            for column in self.config.columns:
                th = html.th().classes(f"{CLASSES_PREFIX}-th {CLASSES_PREFIX}-th-{column.name}")
                if column.width_percent is not None:
                    th.style(f"width: {column.width_percent}%")
                with th:
                    ui.label(column.label or column.name)
            # Subclasses can override to add button columns
            self._build_header_buttons()

    def _build_header_buttons(self):
        """Override in subclasses to add header buttons"""
        pass

    @ui.refreshable
    async def build(self):
        """Build the table UI - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement build()")

    # ============= Helper Methods for Common CRUD Operations =============

    def _notify(self, message: str, **kwargs) -> None:
        """Show notification using ui.notify from context.client"""
        with self._client:      # avoid issues with (eg button) event context disappearing
            ui.notify(message, **kwargs)

    def _validate(self, item: dict, notify: bool = True) -> tuple[bool, dict]:
        """Validate item with optional error notification.

        Args:
            item: Item or partial item to validate
            notify: If True, show notification on validation error

        Returns:
            Tuple of (is_valid, error_dict)
        """
        (valid, error_dict) = self.data_source.validate(item)

        if not valid and notify:
            self._notify(
                f"{error_dict['col_name']} {error_dict['error_value']}: {error_dict['error_msg']}",
                type="warning",
                timeout=1500,
            )

        return (valid, error_dict)

    async def _validate_and_create(self, item: dict) -> bool:
        """Validate item, create it - observers handle refresh automatically."""
        (valid, _) = self._validate(item)

        if valid:
            await self.data_source.create_item(item)
            self._notify("Item created", type="positive")
            return True

        return False

    async def _update(self, item_id: int, partial_item: dict) -> bool:
        """Validate and update item - observers handle refresh automatically."""
        (valid, _) = self._validate(partial_item)

        if valid:
            updated_item = await self.data_source.update_item(item_id, partial_item)
            if updated_item:
                self._notify("Item updated", type="positive")
                return True
            else:
                self._notify("Update failed", type="negative")
                return False

        return False

    async def _delete(self, item: dict, confirm: bool | None = None) -> bool:
        """Delete item with optional confirmation dialog - observers handle refresh automatically."""
        confirm = confirm if confirm is not None else self.config.delete_confirmation

        if confirm:
            if not await confirm_dialog({
                'question': 'Delete item?',
                'explanation': 'This action cannot be undone',
                'no_button': 'Cancel',
                'yes_button': 'Delete'
            }, item):
                return False

        await self.data_source.delete_item(item)
        self._notify("Item deleted", type="info")
        return True


async def confirm_dialog(prompts: dict = {}, item: dict = {}):
    """Show a confirmation dialog.

    Args:
        prompts: Dict with keys 'question', 'explanation', 'yes_button', 'no_button'
                 Values can use {field_name} format strings that will be filled from item
        item: Item data for format string substitution

    Returns:
        True if user confirmed, False if cancelled
    """
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
