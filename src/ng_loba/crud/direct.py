"""
Direct edit CRUD table - inline editing with auto-save on blur.
Uses div-based flexbox layout with crudy-* classes.
"""

from typing import Any

from nicegui import ui

from .base import TableConfig
from ._table_base import BaseCrudTable
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

    def _build_header(self):
        """Build header row using divs with flexbox pattern"""
        with ui.row().classes("crudy-header"):
            for column in self.config.columns:
                ui.label(column.label or column.name).classes(f"crudy-col-{column.name}").style(column.width_style)
            # Empty header for actions column - no width_style, fills remaining space
            ui.label("").classes("crudy-col-actions")

    @ui.refreshable
    async def build(self):
        """Build direct-edit table using divs with flexbox layout"""
        await self.load_data()
        with ui.card().classes("crudy-card crudy-direct-mode"):
            self._build_header()
            self._build_body()  # type: ignore

    @ui.refreshable
    def _build_body(self):
        """Build table body with always-editable rows"""
        for row_index, row in enumerate(self.data):
            with ui.row().classes("crudy-row"):
                self._build_data_row(row_index, row)
                # Delete button
                if self.config.show_delete_button:
                    with ui.element("div").classes("crudy-col-actions"):
                        ui.button(icon="bi-trash",
                                  on_click=lambda _, r=row: self._handle_delete(r)) \
                            .props("flat dense size=md").classes("crudy-btn-icon")

        # New item row (shown when toggled)
        if self.state["show_new_item"]:
            with ui.row().classes("crudy-row crudy-new-row"):
                self._build_data_row(None, self.new_item)
                with ui.element("div").classes("crudy-col-actions"):
                    ui.button(icon="bi-check-square", color="grey",
                              on_click=lambda: self._handle_add(self.new_item)) \
                        .props("flat dense size=md").classes("crudy-btn-icon") \
                        .bind_enabled_from(self.state, "new_item_valid")

        # Add button row (shown when new item row is hidden)
        if self.config.add_button and not self.state["show_new_item"]:
            with ui.row().classes("crudy-add-row"):
                ui.label(self.config.add_button) \
                    .on("click", self._toggle_new_item) \
                    .classes("crudy-add-button")

    def _build_data_row(self, row_index: int | None, item: dict[str, Any]) -> None:
        """Build a single data row (editable)"""
        new_row = row_index is None

        for col in self.config.columns:
            col_name = col.name

            if col.ui_type:
                cls = col.ui_type
                cls_parms = col.parms.copy()
                cls_parms["value"] = item[col_name]
                props = col.props or ""

                if new_row:
                    cls_parms["on_change"] = lambda: self._handle_change(item)
                    # Don't disable columns in new item
                    props = props.replace("disable", "")

                with ui.element("div").classes(f"crudy-col-{col_name}").style(col.width_style):
                    el = cls(**cls_parms).classes("crudy-input").bind_value(item, col_name)
                    combined_props = f"dense flat {props}".strip()
                    el.props(combined_props)
                    el.on("blur", lambda item=item, col_name=col_name: self._handle_blur(col_name, item))

    def _toggle_new_item(self) -> None:
        """Toggle new item row visibility"""
        self.state["show_new_item"] = not self.state["show_new_item"]
        self._build_body.refresh()  # type: ignore

    def _handle_change(self, new_item: dict[str, Any]) -> None:
        """Handle change event (optional validation while typing)"""
        # Optionally validate while typing?
        # (valid, _) = self.store.validate(new_item)
        # self.state["new_item_valid"] = valid
        pass

    async def _handle_blur(self, col_name: str, item: dict[str, Any]) -> None:
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
            await self._update(id, partial)

    async def _handle_add(self, new_item: dict[str, Any]) -> None:
        """Handle adding new item"""
        if await self._validate_and_create(new_item):
            self.reset()
            self._build_body.refresh()
        else:
            self.state['new_item_valid'] = False

    async def _handle_delete(self, row: dict[str, Any]) -> None:
        """Handle row deletion - direct mode uses no confirmation by default"""
        await self._delete(row, confirm=False)
