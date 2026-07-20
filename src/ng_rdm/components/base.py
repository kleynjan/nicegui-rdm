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
from ..utils import logger

_UNSET: Any = object()   # "argument not given", so requery(q=None) can clear a predicate


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
    sortable: bool = False                                   # if True, header is clickable to sort by this column
    sort_key: Optional[str] = None                           # field passed to order_by when sorting (defaults to name)
    sort_desc_first: bool = False                            # open descending on first click (dates, counts)
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
    # Each toolbar element carries its own slot, so search-top / pager-bottom is expressible
    toolbar_position: Literal["top", "bottom"] = "bottom"   # add button + render_toolbar
    search_position: Literal["top", "bottom"] = "top"
    pager_position: Literal["top", "bottom"] = "bottom"
    # Pager — needs limit= on the table. pager_label alone also switches counting on,
    # for apps that bind their own chrome to the published state keys.
    show_pager: bool = False
    pager_label: Optional[Callable[[int, int, int], str]] = None   # (first, last, total) → str
    # Search — wants auto_observe=False; q takes no part in topic routing
    show_search: bool = False
    search_fields: list[str] = field(default_factory=list)
    search_placeholder: Optional[str] = None
    search_debounce: int = 300                                     # ms

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
        q: Any | None = None,
        transform: Callable[[list[dict]], list[dict]] | None = None,
        limit: int | None = None,
        offset: int = 0,
        order_by: list[str] | None = None,
    ):
        """Load data from data source with optional filter, predicate, transform and bounded window."""
        self.data = await self.data_source.read_items(
            join_fields=join_fields or [],
            filter_by=filter_by,
            q=q,
            limit=limit,
            offset=offset,
            order_by=order_by,
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
    - TableConfig, filter_by, q, transform, extra join fields
    - load_data() with join field merging
    - Bounded window (limit/offset/order_by) held in state for query-view paging
    - Toolbar rendering (add button; filtering/pagination in future)

    For large entities, pass limit=/order_by= and auto_observe=False to make this a
    bounded "query-view"; the offset in state supports paging on the render_toolbar hook.

    `q` carries non-equality filtering (a Tortoise Q; a callable predicate on DictStore) —
    assign `table.q` then `await table.build.refresh()` to drive a search box. Unlike
    filter_by it takes no part in topic routing, so observe() still subscribes on filter_by.
    """

    def __init__(
        self,
        data_source: RdmDataSource,
        config: TableConfig,
        state: dict | None = None,
        *,
        filter_by: dict[str, Any] | None = None,
        q: Any | None = None,
        transform: Callable[[list[dict]], list[dict]] | None = None,
        join_fields: list[str] | None = None,
        on_add: Callable[[], Awaitable[None] | None] | None = None,
        render_toolbar: Callable[[], Any] | None = None,   # sync or async; awaited if awaitable
        auto_observe: bool = True,
        limit: int | None = None,
        order_by: list[str] | None = None,
    ):
        super().__init__(data_source=data_source, state=state)
        self.config = config
        self.filter_by = filter_by
        self.q = q
        self.transform = transform
        self._extra_join_fields = join_fields or []
        self.on_add = on_add
        self.render_toolbar = render_toolbar
        self.order_by = order_by
        self.row_key = "id"  # tie-break field for stable sort/paging; subclasses may override
        self._search_q: Any | None = None
        self.state.setdefault("limit", limit)
        self.state.setdefault("offset", 0)
        # Seed the published keys: a top-positioned pager binds before the first read,
        # and an unseeded key would leave it blank with both buttons enabled.
        self.state.setdefault("total", None)
        self.state.setdefault("shown", 0)
        self.state.setdefault("page_first", 0)
        self.state.setdefault("page_last", 0)
        self.state.setdefault("has_prev", False)
        self.state.setdefault("has_next", False)
        self.state.setdefault("page_label", "")
        if auto_observe:
            self.observe(topics=filter_by)

    async def load_data(
        self,
        join_fields: list[str] | None = None,
        filter_by: dict[str, Any] | None = None,
        q: Any | None = None,
        transform: Callable[[list[dict]], list[dict]] | None = None,
        limit: int | None = None,
        offset: int = 0,
        order_by: list[str] | None = None,
    ):
        all_joins = list(set(self.config.join_fields + self._extra_join_fields))
        read: dict[str, Any] = dict(
            join_fields=join_fields or all_joins,
            filter_by=filter_by if filter_by is not None else self.filter_by,
            q=self._effective_q(q),
            transform=transform if transform is not None else self.transform,
            limit=limit if limit is not None else self.state.get("limit"),
            offset=offset or self.state.get("offset", 0),
            order_by=order_by if order_by is not None else self.order_by,
        )
        await super().load_data(**read)
        await self._publish_page_state(read)

    async def requery(self, *, q: Any = _UNSET, filter_by: Any = _UNSET, order_by: Any = _UNSET, offset: int = 0):
        """Change the query and re-render in one step (assignments alone are order-sensitive).

        Only the arguments given are changed; `offset` resets to the first page by default.

        A new `filter_by` also moves the observer subscription with it, so an observed
        table keeps reacting to its *new* scope — but only when the subscription was
        tracking `filter_by` in the first place. A table given explicit topics via
        `observe(topics=...)` keeps them; call `reobserve()` yourself to change those.
        """
        if q is not _UNSET:
            self.q = q
        if filter_by is not _UNSET:
            tracking_filter = self._is_observing and self._observed_topics == self.filter_by
            self.filter_by = filter_by
            if tracking_filter:
                self.reobserve(topics=filter_by)
        if order_by is not _UNSET:
            self.order_by = order_by
        self.state["offset"] = offset
        await self.build.refresh()  # type: ignore

    # ── Paging / search state ──
    # The toolbar is rendered once (see render()), so paging chrome cannot react by being
    # re-rendered. Instead every read publishes its numbers into self.state — total, shown,
    # page_first, page_last, has_prev, has_next, page_label — and the chrome binds to them.
    # The raw keys are the point: an app can bind its own counter with its own wording.

    def _effective_q(self, q: Any | None) -> Any | None:
        """Compose the caller's predicate with the search box's, so both apply."""
        base = q if q is not None else self.q
        if self._search_q is None:
            return base
        return self._data_source_method("and_q")(base, self._search_q)

    def _data_source_method(self, name: str) -> Callable[..., Any]:
        """Fetch a predicate-building method, with a clear error for older data sources."""
        method = getattr(self.data_source, name, None)
        if method is None:
            raise TypeError(
                f"{type(self.data_source).__name__} has no {name}() — search needs a data source "
                f"implementing the RdmDataSource predicate methods (search_q/and_q)."
            )
        return method

    def _wants_counts(self) -> bool:
        """A COUNT per read is only worth it if something displays the total."""
        return self.config.show_pager or self.config.pager_label is not None

    async def _publish_page_state(self, read: dict) -> None:
        """Publish the window's numbers into state for bound (never re-rendered) chrome.

        Counting is skipped when the answer is free — a first page that came back under its
        own limit is the whole result set — and when nothing displays a total, so an
        observed table does not add a COUNT per store event.
        """
        limit, offset = read["limit"], read["offset"]
        shown = len(self.data)
        if offset == 0 and (limit is None or shown < limit):
            total = shown
        elif self._wants_counts():
            counted = await self.data_source.read_counts(filter_by=read["filter_by"], q=read["q"])
            total = counted if isinstance(counted, int) else sum(counted.values())
            if not shown and offset:  # window fell off the end (rows deleted) — step back
                read["offset"] = offset = self.state["offset"] = ((total - 1) // limit) * limit if (total and limit) else 0
                await super().load_data(**read)
                shown = len(self.data)
        else:
            total = None

        self.state.update(
            total=total,
            shown=shown,
            page_first=offset + 1 if shown else 0,
            page_last=offset + shown,
            has_prev=offset > 0,
            has_next=(offset + shown < total) if total is not None else (limit is not None and shown == limit),
        )
        label = self.config.pager_label or self._default_page_label
        self.state["page_label"] = label(self.state["page_first"], self.state["page_last"], total or 0)

    def _default_page_label(self, first: int, last: int, total: int) -> str:
        return f"{first}–{last} {_('of')} {total}" if total else _("No data")

    async def _page(self, direction: int) -> None:
        """Step one page and refresh; the bound pager follows the published state."""
        limit = self.state.get("limit")
        if not limit:
            return
        self.state["offset"] = max(0, self.state.get("offset", 0) + direction * limit)
        await self.build.refresh()  # type: ignore

    async def _on_search(self, text: str | None) -> None:
        """Rebuild the search predicate, return to page 1, refresh."""
        text = (text or "").strip()
        self._search_q = self._data_source_method("search_q")(text, self.config.search_fields) if text else None
        self.state["offset"] = 0
        await self.build.refresh()  # type: ignore

    # ── Header-click sorting ──
    # Sort state lives on the instance (self.order_by), not in self.state, so
    # components subscribed to the same store sort independently. The actual sort
    # is delegated to read_items(order_by=...) via load_data() — never to the
    # store's shared set_sort_key().

    def _sort_field(self, col: Column) -> str:
        """The field a column sorts on. Resolved here, not on Column: a derived name's
        query_map lives on the store, which is not attached when Column is constructed."""
        if col.sort_key:
            return col.sort_key
        query_map = getattr(self.data_source, "_query_map", {})
        return query_map.get(col.name, [col.name])[0]

    def _active_sort(self) -> tuple[str | None, bool]:
        """Return (field, reverse) of the current primary sort, or (None, False)."""
        if not self.order_by:
            return None, False
        first = self.order_by[0]
        return (first[1:], True) if first.startswith("-") else (first, False)

    async def _toggle_sort(self, col: Column) -> None:
        """Flip ascending↔descending on a column's field, reset paging, and refresh."""
        field = self._sort_field(col)
        active_field, active_reverse = self._active_sort()
        reverse = not active_reverse if field == active_field else col.sort_desc_first
        order = [f"-{field}" if reverse else field]
        if self.row_key != field:
            order.append(self.row_key)  # stable tie-break for deterministic paging
        self.order_by = order
        self.state["offset"] = 0
        await self.build.refresh()  # type: ignore

    def _render_column_headers(self) -> None:
        """Render a <th> per data column; sortable columns get a click handler + indicator.

        Shared by ListTable/ActionButtonTable/SelectionTable. Each caller supplies its
        own leading/trailing header cells (checkbox, actions) around this call.
        """
        active_field, active_reverse = self._active_sort()
        for col in self.config.columns:
            if col.sortable:
                is_active = self._sort_field(col) == active_field
                icon = ("caret-down-fill" if active_reverse else "caret-up-fill") if is_active else "arrow-down-up"
                state = "rdm-sort-active" if is_active else "rdm-sort-inactive"
                th = html.th().classes("rdm-sortable").mark(f"rdm-sort-{col.name}")
                th.on("click", lambda _, c=col: self._toggle_sort(c))
                with th:
                    with html.div().classes("rdm-th-sort"):
                        html.span(col.label or col.name)
                        ui.html(f'<i class="bi bi-{icon}"></i>', sanitize=False).classes(f"rdm-sort-indicator {state}")
            else:
                th = html.th(col.label or col.name)
            if col.width_percent:
                th.style(f"width: {col.width_percent}%")

    def _render_empty_row(self, colspan: int) -> None:
        """Empty state as a row inside the table, so headers and sorting survive it."""
        with html.tr():
            with html.td().props(f"colspan={colspan}"):
                ui.label(self.config.empty_message or _("No data")).classes("rdm-text-muted")

    def _render_search(self) -> None:
        """Search input — rendered once, so it keeps focus and value across refreshes."""
        ui.input(placeholder=self.config.search_placeholder or _("Search")) \
            .props(f'debounce={self.config.search_debounce} clearable') \
            .classes("rdm-search").mark("rdm-search") \
            .on_value_change(lambda e: self._on_search(e.value))

    def _render_pager(self) -> None:
        """Pager — bound to the state published by each read; never re-rendered."""
        from .widgets.button import IconButton
        if not self.state.get("limit"):
            logger.warning("ng_rdm: show_pager needs limit= on the table — the pager cannot page without one")
        with html.div().classes("rdm-pager"):
            IconButton("chevron-left", color="secondary", tooltip=_("Previous page"),
                       on_click=lambda: self._page(-1)).classes("rdm-pager-btn") \
                .bind_enabled_from(self.state, "has_prev")
            ui.label().classes("rdm-pager-label").bind_text_from(self.state, "page_label")
            IconButton("chevron-right", color="secondary", tooltip=_("Next page"),
                       on_click=lambda: self._page(1)).classes("rdm-pager-btn") \
                .bind_enabled_from(self.state, "has_next")

    async def _build_toolbar(self, at: Literal["top", "bottom"]):
        """Render whichever toolbar elements are assigned to the given slot.

        Called once from render(), outside the refreshable: stateful widgets keep their
        focus and value, and data-dependent parts bind to self.state instead of being
        re-rendered. Both slots are visited; each renders only what is assigned to it.
        """
        own_slot = at == self.config.toolbar_position
        show_add = own_slot and self.config.show_add_button and self.on_add is not None
        show_custom = own_slot and self.render_toolbar is not None
        show_search = self.config.show_search and at == self.config.search_position
        show_pager = self.config.show_pager and at == self.config.pager_position
        if not (show_add or show_custom or show_search or show_pager):
            return
        with html.div().classes("rdm-table-toolbar"):
            if show_search:
                self._render_search()
            if show_add:
                from .widgets.button import Button
                Button(self.config.add_button or _("Add new"), on_click=self.on_add)
            if self.render_toolbar and show_custom:
                result = self.render_toolbar()
                if result is not None and hasattr(result, '__await__'):
                    await result
            if show_pager:
                self._render_pager()

    async def render(self):
        """Render the toolbars once and the table itself. Public entry point.

        build() stays refreshable and re-renders headers and rows only; anything in a
        toolbar slot is rendered once here and reacts by binding to self.state.
        """
        await self._build_toolbar("top")
        await self.build()
        await self._build_toolbar("bottom")

    async def build_with_toolbars(self):
        """Deprecated — use render()."""
        logger.warning("ng_rdm: build_with_toolbars() is deprecated, use render()")
        await self.render()

    async def build(self):
        """Subclasses must implement build() to render the table itself."""
        raise NotImplementedError("Subclasses must implement build()")


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
