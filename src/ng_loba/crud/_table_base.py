"""
Base class for CRUD table implementations.
"""

from nicegui import html, ui

from .base import StoreComponent, Column, TableConfig, confirm_dialog
from .protocol import CrudDataSource


class BaseCrudTable(StoreComponent):
    """Base class for CRUD table implementations"""

    def __init__(self, state: dict, data_source: CrudDataSource, config: TableConfig):
        super().__init__(state, data_source)
        self.config = config

    async def load_data(self, join_fields: list[str] | None = None):
        """Load data from data source using config's join_fields"""
        self.data = await self.data_source.read_items(
            join_fields=join_fields or self.config.join_fields
        )

    def _build_header(self):
        """Build table header - common to both modes"""
        with html.tr().classes("crudy-header-tr"):
            for column in self.config.columns:
                th = html.th().classes(f"crudy-th crudy-th-{column.name}")
                if column.width_percent is not None:
                    th.style(f"width: {column.width_percent}%")
                with th:
                    ui.label(column.label or column.name)
            self._build_header_buttons()

    def _build_header_buttons(self):
        """Override in subclasses to add header buttons"""
        pass

    async def _delete(self, item: dict, confirm: bool | None = None) -> bool:
        """Delete item with optional confirmation - uses config.delete_confirmation as default"""
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
