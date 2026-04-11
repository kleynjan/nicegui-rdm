"""
Base component for store-connected UI elements.

Provides observer pattern for automatic refresh on store changes,
RDM helpers with validation, and notification utilities.
"""

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Literal, Optional

from nicegui import html, ui

from .i18n import _
from .protocol import RdmDataSource
from ..store.notifier import StoreEvent


@dataclass
class RowAction:
    """Configuration for a row action button.

    Renders as icon if `icon` is provided, otherwise as text button using `label`.

    Args:
        icon: Bootstrap icon name (e.g., "send", "eye", "trash") — if set, renders as icon
        label: Text for button (used when no icon)
        tooltip: Hover tooltip text
        callback: Async or sync function called with row dict when clicked
        color: Button/icon color: "primary", "secondary", "danger"
    """
    icon: str | None = None                                  # Icon name — if set, renders as icon
    label: str | None = None                                 # Button text (used when no icon)
    tooltip: str = ""                                        # Hover tooltip text
    callback: Callable[[dict], Awaitable[None] | None] | None = None  # Called with row data
    color: str = "primary"                                   # "primary", "secondary", "danger", etc.

    def render(self, row: dict, mark: str = "") -> None:
        """Render this action for the given row."""
        from .widgets.button import Button, Icon

        def handler(_, r=row):
            return self._invoke(r)

        if self.icon:
            el = Icon(self.icon, on_click=handler, color=self.color, tooltip=self.tooltip or None)
        elif self.label:
            el = Button(self.label, color=self.color, on_click=handler).classes("rdm-btn-sm")
        else:
            return  # Nothing to render
        if mark:
            el.mark(mark)

    async def _invoke(self, row: dict):
        """Invoke callback with row data, handling async."""
        if self.callback:
            result = self.callback(row)
            if result is not None and hasattr(result, '__await__'):
                await result


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
    """Configuration for table display components (ActionButtonTable, ListTable, SelectionTable)."""
    columns: list[Column] = field(default_factory=list)
    empty_message: Optional[str] = None
    add_button: Optional[str] = None
    show_add_button: bool = True
    show_edit_button: bool = True
    show_delete_button: bool = True
    custom_actions: list[RowAction] = field(default_factory=list)
    toolbar_position: Literal["top", "bottom"] = "bottom"

    def __post_init__(self):
        self.join_fields = list({col.name for col in self.columns if "__" in col.name})
        for col in self.columns:
            col.width_style = f"flex: 0 0 {col.width_percent}%" if col.width_percent is not None else ""


@dataclass
class FormConfig:
    """Configuration for form/dialog components."""
    columns: list[Column] = field(default_factory=list)
    title_add: Optional[str] = None
    title_edit: Optional[str] = None
    dialog_class: Optional[str] = None
    focus_column: Optional[str] = None
    delete_confirmation: bool = True

    def __post_init__(self):
        if not self.focus_column and self.columns:
            self.focus_column = self.columns[0].name
        for col in self.columns:
            col.width_style = f"flex: 0 0 {col.width_percent}%" if col.width_percent is not None else ""


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
                f"{error_dict['col_name']} {error_dict['error_value']}: {_(error_dict['error_msg'])}",
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
    Call observe() at page level after construction for explicit lifecycle management.
    """

    def __init__(self, data_source: RdmDataSource, state: dict | None = None):
        super().__init__(data_source)
        self.state = state if state is not None else {}
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
            html.span(display).classes("rdm-link rdm-on-click").on(
                "click", lambda _, r=row, h=handler: h(r)
            )
        else:
            display = col.formatter(value) if col.formatter else (str(value) if value else "")
            html.span(display).classes(f"rdm-cell-{col.name}")

    # ── Subclass contract ──
    # Subclasses MUST implement:
    #
    #     @ui.refreshable_method
    #     async def build(self) -> None:
    #         ...
    #
    # This method is called by _handle_datasource_change (via getattr) to refresh
    # the UI when the data source changes. The @ui.refreshable_method decorator
    # provides .refresh(), .prune(), and .targets used for lifecycle management.
    #
    # Why not defined here: NiceGUI's refreshable_method uses an invariant TypeVar
    # (_S) that makes any override in a subclass a Pylance type error — whether
    # the base uses the decorator or not. Defining build here (decorated or plain)
    # produces reportIncompatibleVariableOverride / reportIncompatibleMethodOverride
    # that cannot be suppressed without global config or per-subclass ignores.

    async def _handle_datasource_change(self, event: StoreEvent):
        """Handle data source changes. Auto-unobserves if DOM context is gone."""
        build = getattr(self, 'build', None)
        if build and hasattr(build, 'prune'):
            build.prune()
            if not [t for t in build.targets if t.instance == self]:
                self.unobserve()
                return

        await self.build.refresh()      # type: ignore


class ObservableRdmTable(ObservableRdmComponent):
    """Base class for store-connected table components.

    Adds shared table concerns on top of ObservableRdmComponent:
    - TableConfig, filter_by, transform, extra join fields
    - load_data() with join field merging
    - Toolbar rendering (add button; filtering/pagination in future)
    """

    def __init__(
        self,
        data_source: RdmDataSource,
        config: TableConfig,
        state: dict | None = None,
        *,
        filter_by: dict[str, Any] | None = None,
        transform: Callable[[list[dict]], list[dict]] | None = None,
        join_fields: list[str] | None = None,
        on_add: Callable[[], Awaitable[None] | None] | None = None,
        render_toolbar: Callable[[], None] | None = None,
        auto_observe: bool = True,
    ):
        super().__init__(data_source=data_source, state=state)
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

    def _build_toolbar(self, at: Literal["top", "bottom"] = "top"):
        """Render table toolbar at the given slot position.

        Subclasses call this twice — once before and once after the table —
        passing the slot name. Only the call matching config.toolbar_position renders.
        """
        if at != self.config.toolbar_position:
            return
        if not self.config.show_add_button and not self.render_toolbar:
            return
        with html.div().classes("rdm-table-toolbar"):
            if self.config.show_add_button:
                from .widgets.button import Button
                add_handler = self.on_add or self._default_on_add
                Button(self.config.add_button or _("Add new"), on_click=add_handler)
            if self.render_toolbar:
                self.render_toolbar()

    async def build_with_toolbars(self):
        """Build the table with toolbars. Call this instead of build() if using toolbars."""
        self._build_toolbar("top")
        await self.build()
        self._build_toolbar("bottom")

    async def build(self):
        """Subclasses must implement build() to render the table itself."""
        raise NotImplementedError("Subclasses must implement build()")

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
                from .widgets.button import Button
                with html.div().classes("rdm-dialog-footer"):
                    Button(yes_button, color="danger", on_click=lambda: d.submit(True))
                    Button(no_button, color="secondary", on_click=lambda: d.submit(False))

    result = await dialog
    return result
