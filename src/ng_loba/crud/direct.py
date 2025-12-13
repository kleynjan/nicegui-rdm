"""
Direct edit CRUD table - inline editing with auto-save on blur.
Based on alarm/components/crud_table.py
"""

from typing import Any, Dict

from nicegui import html, ui

from .base import BaseCrudTable, CLASSES_PREFIX, TableConfig
from .protocol import CrudDataSource


class DirectEditTable(BaseCrudTable):
    """Direct edit mode - inline editing with auto-save on blur"""

    def __init__(self, state: dict, data_source: CrudDataSource, config: TableConfig):
        super().__init__(state, data_source, config)
        self.reset()

    def reset(self):
        """Reset table state"""
        self.state.update({
            "show_new_item": False,
            "new_item_valid": False,
            "current_error": {}
        })
        self.new_item = {
            col.name: col.default_value
            for col in self.config.columns
        }

    def _build_header_buttons(self):
        """Add button column header"""
        with html.th().classes(f"{CLASSES_PREFIX}-th-button"):
            ui.label("")

    @ui.refreshable
    async def build(self):
        """Build direct-edit table"""
        await self.load_data()
        with html.table().classes(f"{CLASSES_PREFIX}-table {CLASSES_PREFIX}-direct-mode"):
            self._build_header()
            self._build_body()  # type: ignore

    @ui.refreshable
    def _build_body(self):
        """Build table body with always-editable rows"""
        with html.tbody().classes(f"{CLASSES_PREFIX}-tbody"):
            for row_index, row in enumerate(self.data):
                with html.tr().classes(f"{CLASSES_PREFIX}-row-tr"):
                    self._build_data_row(row_index, row)
                    if not self.config.skip_delete:
                        with html.td().classes(f"{CLASSES_PREFIX}-td-button"):
                            ui.button(icon="delete") \
                                .on("click", lambda _, r=row: self._handle_delete(r)) \
                                .classes(f"{CLASSES_PREFIX}-column-button")

            # New item row (shown when toggled)
            if self.config.add_button:
                with html.tr().classes(f"{CLASSES_PREFIX}-row-tr") \
                        .bind_visibility_from(self.state, "show_new_item"):
                    self._build_data_row(None, self.new_item)
                    with html.td().classes(f"{CLASSES_PREFIX}-td-button"):
                        ui.button(icon="save", on_click=lambda: self._handle_add(self.new_item)) \
                            .classes(f"{CLASSES_PREFIX}-column-button positive") \
                            .bind_enabled_from(self.state, "new_item_valid")

                # Add button row (shown when new item row is hidden)
                with html.tr().classes(f"{CLASSES_PREFIX}-add-button-row") \
                        .bind_visibility_from(self.state, "show_new_item", backward=lambda x: not x):
                    with html.td().props(f"colspan={len(self.config.columns) + 1}"):
                        ui.label(self.config.add_button) \
                            .on("click", self._toggle_new_item) \
                            .classes(f"{CLASSES_PREFIX}-add-button")

    def _build_data_row(self, row_index: int | None, item: Dict[str, Any]) -> None:
        """Build a single data row (editable)"""
        new_row = row_index is None

        for col in self.config.columns:
            col_name = col.name
            if col.ui_type:
                cls = col.ui_type
                cls_parms = col.parms.copy()
                cls_parms["value"] = item[col_name]
                props = col.props

                if new_row:
                    cls_parms["on_change"] = lambda: self._handle_change(item)
                    if props:
                        # Don't disable columns in new item
                        props = props.replace("disable", "")

                with html.td().classes(f"{CLASSES_PREFIX}-td {CLASSES_PREFIX}-td-{col_name}"):
                    el = (
                        cls(**cls_parms)
                        .classes(f"{CLASSES_PREFIX}-input {CLASSES_PREFIX}-input-{col_name}")
                        .bind_value(item, col_name)
                    )
                    el.props(props)
                    el.on("blur", lambda item=item, col_name=col_name: self._handle_blur(col_name, item))

    def _toggle_new_item(self) -> None:
        """Toggle new item row visibility"""
        self.state["show_new_item"] = not self.state["show_new_item"]

    def _handle_change(self, new_item: Dict[str, Any]) -> None:
        """Handle change event (optional validation while typing)"""
        # Optionally validate while typing
        # (valid, _) = self.store.validate(new_item)
        # self.state["new_item_valid"] = valid
        pass

    async def _handle_blur(self, col_name: str, item: Dict[str, Any]) -> None:
        """Validate and save on blur"""
        id = item.get("id", None)

        # Create partial update dict for the changed field
        col = self.config.find_column(col_name)
        if col and col.ui_type == ui.checkbox:
            # Checkbox blurs before updating, so we need to invert the value
            partial = {col_name: not item[col_name]}
        else:
            partial = {col_name: item[col_name]}

        # Validate the blurred field
        (valid, error_dict) = self.data_source.validate(partial)

        if valid:
            # Check if entire row is valid
            (valid_all, error_dict) = self.data_source.validate(item)
            if valid_all:
                self.state["new_item_valid"] = True
        else:
            ui.notify(
                f"{error_dict['col_name']} {error_dict['error_value']}: {error_dict['error_msg']}",
                type="warning",
                timeout=1500,
            )
            self.state["new_item_valid"] = False
            self.state["current_error"] = error_dict

        # Update data source if valid and has id (existing item)
        if valid and id is not None:
            await self.data_source.update_item(id, partial)

    async def _handle_add(self, new_item: Dict[str, Any]) -> None:
        """Handle adding new item"""
        (valid, error_dict) = self.data_source.validate(new_item)
        if valid:
            if self.config.on_add:
                await self.config.on_add(new_item)
            else:
                await self.data_source.create_item(new_item)
            self.reset()
            self.build.refresh()
        else:
            self.state['new_item_valid'] = False
            ui.notify(
                f"{error_dict['col_name']} {error_dict['error_value']}: {error_dict['error_msg']}",
                type="warning",
                timeout=1500,
            )

    async def _handle_delete(self, row: Dict[str, Any]) -> None:
        """Handle row deletion"""
        await self.data_source.delete_item(row)
        self.build.refresh()
