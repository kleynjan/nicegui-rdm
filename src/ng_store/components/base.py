"""
Base component for store-connected UI elements.

Provides observer pattern for automatic refresh on store changes,
CRUD helpers with validation, and notification utilities.
"""

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from nicegui import ui

from .i18n import _
from .protocol import CrudDataSource
from ..store import StoreEvent


class CrudComponent:
    """Base for ng_crud UI components needing client context capture.

    Captures ui.context.client at construction for safe notifications
    in async callbacks that run after UI may have been rebuilt.
    """
    def __init__(self):
        self._client = ui.context.client

    def _notify(self, message: str, **kwargs) -> None:
        with self._client:
            ui.notify(message, **kwargs)


@dataclass
class RowAction:
    """Configuration for a custom row action button.

    Can render as icon button or text button depending on fields and table's action_style.

    Resolution logic:
    - If variant is set, use that style
    - Otherwise, follow table's action_style:
      - action_style="icon": use icon if provided, else fall back to label
      - action_style="button": use label if provided, else fall back to icon with tooltip

    Args:
        icon: Bootstrap icon name (e.g., "send", "eye", "trash")
        label: Text for button (used in button mode)
        tooltip: Hover tooltip text
        callback: Async or sync function called with row dict when clicked
        variant: Override style ("icon", "primary", "secondary", "danger")
                 If None, follows table's action_style
    """
    icon: str | None = None                                  # Icon name (e.g., "send", "visibility")
    label: str | None = None                                 # Button text (for button style)
    tooltip: str = ""                                        # Hover tooltip text
    callback: Callable[[dict], Awaitable[None] | None] | None = None  # Called with row data
    variant: str | None = None                               # "icon", "primary", "secondary", "danger", or None


@dataclass
class Column:
    """Configuration for a table column or dialog field"""
    name: str
    label: Optional[str] = None
    ui_type: Optional[Any] = None
    default_value: Any = ""
    parms: dict[str, Any] = field(default_factory=dict)      # passed to the ui_type instance
    props: Optional[str] = ""                                # passed to el.props()
    width_percent: Optional[float] = None                    # column width as percentage (0-100)
    placeholder: Optional[str] = None                        # placeholder text for modal inputs
    required: bool = False                                   # validation: field cannot be empty
    editable: bool = True                                    # if False, displayed as label in edit mode
    on_click: Callable[[dict], Awaitable[None] | None] | None = None  # per-column click handler
    formatter: Callable[[Any], str] | None = None            # display formatter for table cells
    render: Callable[[dict], None] | None = None             # custom render function (receives row dict)
    width_style: str = ""                                    # computed flex style (set in __post_init__)

    def __post_init__(self):
        """Set type-appropriate defaults for various ui_types"""
        if self.default_value == "" and self.ui_type in (ui.number, ui.select):
            self.default_value = None
        if not self.width_style and self.width_percent is not None:
            self.width_style = f"flex: 0 0 {self.width_percent}%"


@dataclass
class TableConfig:
    """Configuration for CRUD tables and related components.

    For modal mode, use table_columns and dialog_columns separately.
    For direct/explicit modes, use columns (backwards compatible).
    """
    columns: list[Column] = field(default_factory=list)      # for direct/explicit modes
    table_columns: list[Column] = field(default_factory=list)  # modal: columns in table view
    dialog_columns: list[Column] = field(default_factory=list)  # modal: columns in dialog
    mode: str = "explicit"              # "explicit", "direct", or "modal"
    add_button: Optional[str] = None    # Custom add button text
    focus_column: Optional[str] = None  # Default column for focus
    delete_confirmation: bool = True    # Confirm deletes
    dialog_class: Optional[str] = None  # CSS class for modal dialog card
    dialog_title_add: Optional[str] = None    # Dialog title for add (modal mode)
    dialog_title_edit: Optional[str] = None   # Dialog title for edit (modal mode)
    empty_message: Optional[str] = None  # Message to display when table is empty
    # Row action buttons (modal mode)
    show_add_button: bool = True        # Show add button
    show_edit_button: bool = True       # Show edit button per row
    show_delete_button: bool = True     # Show delete button per row
    custom_actions: list[RowAction] = field(default_factory=list)  # Custom action buttons per row

    def __post_init__(self):
        # Backwards compat: if columns set but table_columns/dialog_columns empty, use columns for both
        if self.columns and not self.table_columns:
            self.table_columns = self.columns
        if self.columns and not self.dialog_columns:
            self.dialog_columns = self.columns
        # For non-modal modes, ensure columns is set from table_columns if needed
        if not self.columns and self.table_columns:
            self.columns = self.table_columns

        # Compute join_fields from all column sources
        all_cols = self.columns + self.table_columns + self.dialog_columns
        self.join_fields = list({col.name for col in all_cols if "__" in col.name})

        # Set default focus column
        if not self.focus_column:
            if self.dialog_columns:
                self.focus_column = self.dialog_columns[0].name
            elif self.columns:
                self.focus_column = self.columns[0].name

        # Compute width_style for all columns (always set, empty string if no width_percent)
        for col in all_cols:
            col.width_style = f"flex: 0 0 {col.width_percent}%" if col.width_percent is not None else ""

    def find_column(self, col_name: str) -> Column | None:
        """Find column by name in any column list"""
        for col in self.dialog_columns + self.table_columns + self.columns:
            if col.name == col_name:
                return col
        return None


class StoreComponent(CrudComponent):
    """Base class for UI components connected to a data source.

    Provides:
    - Observer pattern: subscribes to data source events for automatic refresh
    - CRUD helpers: validate, create, update, delete with notifications
    - State management via shared state dict
    """

    def __init__(self, state: dict, data_source: CrudDataSource):
        super().__init__()
        self.data_source = data_source
        self.state = state
        self.data: list[dict[str, Any]] = []
        data_source.add_observer(self._handle_datasource_change)

    async def load_data(self, join_fields: list[str] | None = None):
        """Load data from data source"""
        self.data = await self.data_source.read_items(
            join_fields=join_fields or []
        )

    async def _handle_datasource_change(self, event: StoreEvent):
        """Handle data source changes - subclasses can override for custom behavior"""
        await self.build.refresh()  # type: ignore

    @ui.refreshable
    async def build(self):
        """Build the UI - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement build()")

    def _validate(self, item: dict, notify: bool = True) -> tuple[bool, dict]:
        """Validate item with optional error notification."""
        (valid, error_dict) = self.data_source.validate(item)

        if not valid and notify:
            self._notify(
                f"{error_dict['col_name']} {error_dict['error_value']}: {error_dict['error_msg']}",
                type="warning",
                timeout=1500,
            )

        return (valid, error_dict)

    async def _validate_and_create(self, item: dict) -> dict | None:
        """Validate item, create it. Returns created item or None."""
        (valid, _err) = self._validate(item)

        if valid:
            created = await self.data_source.create_item(item)
            if created:
                self._notify(_("Item created"), type="positive")
            return created
        return None

    async def _update(self, item_id: int, partial_item: dict) -> dict | None:
        """Validate and update item. Returns updated item or None."""
        (valid, _err) = self._validate(partial_item)

        if valid:
            updated_item = await self.data_source.update_item(item_id, partial_item)
            if updated_item:
                self._notify(_("Item updated"), type="positive")
                return updated_item
            else:
                self._notify(_("Update failed"), type="negative")
        return None

    async def _delete(self, item: dict, confirm: bool = True) -> bool:
        """Delete item with optional confirmation. Returns True if deleted."""
        if confirm:
            if not await confirm_dialog({
                'question': _('Delete item?'),
                'explanation': _('This action cannot be undone'),
                'yes_button': _('Delete'),
                'no_button': _('Cancel')
            }, item):
                return False

        await self.data_source.delete_item(item)
        self._notify(_("Item deleted"), type="info")
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

    question = prompts.get('question', _('Are you sure?')).format(**item)
    explanation = prompts.get('explanation', '').format(**item)
    yes_button = prompts.get('yes_button', _('Yes')).format(**item)
    no_button = prompts.get('no_button', _('No')).format(**item)

    with dialog as d, ui.card().classes('delete-card'):
        ui.label(question).classes('question')
        ui.label(explanation).classes('explanation')
        with ui.row().classes('confirm-button-row'):
            ui.button(yes_button).on("click", lambda: d.submit(True)) \
                .classes("confirm-button confirm-button-yes btn-confirm")
            ui.button(no_button).on("click", lambda: d.submit(False)) \
                .classes("confirm-button confirm-button-no btn-cancel")

    result = await dialog
    return result
