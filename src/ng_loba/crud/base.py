"""
Base class for CRUD table implementations.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from nicegui import html, ui

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
    mode: str = "explicit"              # "explicit" or "direct"
    focus_column: Optional[str] = None  # Default column for focus (explicit mode)
    on_add: Optional[Callable] = None   # Optional custom add handler
    skip_delete: bool = False           # Hide delete functionality
    add_button: Optional[str] = None    # Custom add button text
    delete_confirmation: bool = True    # Confirm deletes (explicit mode)

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


class BaseCrudTable:
    """Base class for CRUD table implementations"""

    def __init__(self, state: dict, store: Store, config: TableConfig):
        self.store = store
        self.state = state
        self.config = config
        self.data: List[Dict[str, Any]] = []

    async def load_data(self):
        """Load data from store"""
        self.data = await self.store.read_items(
            join_fields=self.config.join_fields
        )

    def _build_header(self):
        """Build table header - common to both modes"""
        with html.tr().classes(f"{CLASSES_PREFIX}-header-tr"):
            for column in self.config.columns:
                with html.th().classes(f"{CLASSES_PREFIX}-th {CLASSES_PREFIX}-th-{column.name}"):
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

    def refresh(self):
        """Refresh the table"""
        self.build.refresh()
