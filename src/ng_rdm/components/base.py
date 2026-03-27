"""
Base component for store-connected UI elements.

Provides observer pattern for automatic refresh on store changes,
RDM helpers with validation, and notification utilities.
"""

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from nicegui import html, ui

from .i18n import _
from .protocol import RdmDataSource
from ..store import StoreEvent


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


class RdmComponent:
    """Base class for UI components connected to a data source.

    Provides:
    - Client context capture for safe notifications in async callbacks
    - CRUD helpers: validate, create, update, delete with notifications
    - Form helpers: init state from item, build item data from state

    Does NOT include observer subscription or state dict - use ObservableRdmComponent for that.
    """

    def __init__(self, data_source: RdmDataSource):
        self._client = ui.context.client
        self.data_source = data_source

    def _notify(self, message: str, **kwargs) -> None:
        with self._client:
            ui.notification(message, position="bottom-left", timeout=3, **kwargs)

    # ── Form helpers ──

    @staticmethod
    def _init_form_state(columns: list[Column], item: dict | None = None) -> dict[str, Any]:
        """Initialize form state from columns and optional item."""
        state: dict[str, Any] = {}
        for col in columns:
            if item:
                value = item.get(col.name, col.default_value)
                if col.ui_type == ui.number:
                    state[col.name] = value
                else:
                    state[col.name] = value or ""
            else:
                state[col.name] = col.default_value
        return state

    @staticmethod
    def _build_item_data(columns: list[Column], state: dict) -> dict[str, Any]:
        """Build item data dict from form state, with string trimming."""
        item_data: dict[str, Any] = {}
        for col in columns:
            value = state.get(col.name, "")
            if isinstance(value, str):
                value = value.strip() or None
            item_data[col.name] = value
        return item_data

    # ── CRUD helpers ──

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
            if not await confirm_dialog(item):
                return False

        await self.data_source.delete_item(item)
        self._notify(_("Item deleted"), type="info")
        return True


class ObservableRdmComponent(RdmComponent):
    """RdmComponent with reactive data binding via observer pattern.

    Observer subscription is explicit via observe()/unobserve() methods.
    Call observe() at page level after construction for clear lifecycle management.
    """

    def __init__(self, state: dict, data_source: RdmDataSource):
        super().__init__(data_source)
        self.state = state
        self.data: list[dict[str, Any]] = []
        self._observed_topics: dict[str, Any] | None = None
        self._is_observing = False

    def observe(self, topics: dict[str, Any] | None = None) -> None:
        """Start observing data source. Call from page level after construction."""
        if self._is_observing:
            self.unobserve()
        self._observed_topics = topics
        self.data_source.add_observer(self._handle_datasource_change, topics=topics)
        self._is_observing = True

    def unobserve(self) -> None:
        """Stop observing data source."""
        if self._is_observing:
            self.data_source.remove_observer(self._handle_datasource_change)
            self._is_observing = False
            self._observed_topics = None

    def reobserve(self, topics: dict[str, Any] | None = None) -> None:
        """Update subscription topics."""
        self.unobserve()
        self.observe(topics)

    @property
    def is_observing(self) -> bool:
        return self._is_observing

    async def load_data(
        self,
        join_fields: list[str] | None = None,
        filter_by: dict[str, Any] | None = None,
        transform: Callable[[list[dict]], list[dict]] | None = None,
    ):
        """Load data from data source with optional filter and transform."""
        self.data = await self.data_source.read_items(
            join_fields=join_fields or [],
            filter_by=filter_by,
        )
        if transform:
            self.data = transform(self.data)

    def _render_cell(self, col: Column, value: Any, row: dict):
        """Render a single cell value. Subclasses can override for special handling."""
        if col.render:
            col.render(row)
        elif col.on_click:
            raw_value = row.get(col.name, "") or ""
            display = col.formatter(raw_value) if col.formatter else str(raw_value)
            handler = col.on_click
            html.span(display).classes("rdm-link").on(
                "click", lambda _, r=row, h=handler: h(r)
            )
        else:
            display = col.formatter(value) if col.formatter else (str(value) if value else "")
            html.span(display)

    async def _handle_datasource_change(self, event: StoreEvent):
        """Handle data source changes. Auto-unobserves if DOM context is gone."""
        build = getattr(self, 'build', None)
        if build and hasattr(build, 'prune'):
            build.prune()
            if not [t for t in build.targets if t.instance == self]:
                self.unobserve()
                return
        await self.build.refresh()  # type: ignore[union-attr]

    # note, commented out to avoid type confusion
    # async def build(self):
    #     raise NotImplementedError("Subclasses must implement build()")


class ObservableRdmTable(ObservableRdmComponent):
    """Base class for store-connected table components.

    Adds shared table concerns on top of ObservableRdmComponent:
    - TableConfig, filter_by, transform, extra join fields
    - load_data() with join field merging
    - Toolbar rendering (add button; filtering/pagination in future)
    """

    def __init__(
        self,
        state: dict,
        data_source: RdmDataSource,
        config: TableConfig,
        filter_by: dict[str, Any] | None = None,
        transform: Callable[[list[dict]], list[dict]] | None = None,
        join_fields: list[str] | None = None,
        on_add: Callable[[], Awaitable[None] | None] | None = None,
        render_toolbar: Callable[[], None] | None = None,
        auto_observe: bool = True,
    ):
        super().__init__(state, data_source)
        self.config = config
        self.filter_by = filter_by
        self.transform = transform
        self._extra_join_fields = join_fields or []
        self.on_add = on_add
        self.render_toolbar = render_toolbar
        if auto_observe:
            self.observe(topics=filter_by)

    async def load_data(
        self,
        join_fields: list[str] | None = None,
        filter_by: dict[str, Any] | None = None,
        transform: Callable[[list[dict]], list[dict]] | None = None,
    ):
        all_joins = list(set(self.config.join_fields + self._extra_join_fields))
        await super().load_data(
            join_fields=join_fields or all_joins,
            filter_by=filter_by if filter_by is not None else self.filter_by,
            transform=transform if transform is not None else self.transform,
        )

    def _build_toolbar(self):
        """Render table toolbar with add button and optional extra content."""
        if not self.config.show_add_button and not self.render_toolbar:
            return
        with html.div().classes("rdm-table-toolbar"):
            if self.config.show_add_button:
                add_handler = self.on_add or self._default_on_add
                with html.button().classes("rdm-btn rdm-btn-primary").on("click", add_handler):
                    html.span(self.config.add_button or _("Add new"))
            if self.render_toolbar:
                self.render_toolbar()

    def _default_on_add(self):
        """Default add handler — no-op. Subclasses with modal support override this."""
        pass


async def confirm_dialog(item: dict | None = None, prompts: dict | None = None):
    """Show a confirmation dialog with RDM styling.

    Default prompts are for delete confirmation. Override via prompts dict.

    Args:
        item: Item data for format string substitution (optional)
        prompts: Dict with keys 'question', 'explanation', 'yes_button', 'no_button'
                 Values can use {field_name} format strings filled from item

    Returns:
        True if user confirmed, False if cancelled
    """
    dialog = ui.dialog().props('persistent')
    item = item or {}
    prompts = prompts or {}

    question = prompts.get('question', _('Delete item?')).format(**item)
    explanation = prompts.get('explanation', _('This action cannot be undone')).format(**item)
    yes_button = prompts.get('yes_button', _('Delete')).format(**item)
    no_button = prompts.get('no_button', _('Cancel')).format(**item)

    with dialog as d:
        with html.div().classes("rdm-dialog-backdrop rdm-component"):
            with html.div().classes("rdm-dialog").style("max-width: 400px"):
                # Body with question and explanation
                with html.div().classes("rdm-dialog-body"):
                    html.div(question).classes("rdm-confirm-question")
                    if explanation:
                        html.div(explanation).classes("rdm-confirm-explanation")

                # Footer with action buttons
                with html.div().classes("rdm-dialog-footer"):
                    with html.button().classes("rdm-btn rdm-btn-danger").on(
                        "click", lambda: d.submit(True)
                    ):
                        html.span(yes_button)
                    with html.button().classes("rdm-btn rdm-btn-secondary").on(
                        "click", lambda: d.submit(False)
                    ):
                        html.span(no_button)

    result = await dialog
    return result
