"""
EditCard - in-place form for editing or creating a store item.

Renders dialog_columns as form fields inside a card.
Used by ViewStack as the "edit" view in the list → detail → edit flow.
"""
from typing import Any, Callable

from nicegui import html, ui

from .i18n import _
from .base import RdmComponent, TableConfig
from .fields import build_form_field
from .protocol import RdmDataSource


class EditCard(RdmComponent):
    """In-place editing card using dialog_columns config.

    Unlike EditDialog (modal), this renders inline and is managed by ViewStack.
    """

    def __init__(
        self,
        data_source: RdmDataSource,
        config: TableConfig,
        on_saved: Callable[[dict], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
    ):
        super().__init__(data_source)
        self.config = config
        self.on_saved = on_saved
        self.on_cancel = on_cancel
        self._form_state: dict[str, Any] = {}
        self._item_id: int | None = None

    @property
    def is_new(self) -> bool:
        return self._item_id is None

    def set_item(self, item: dict | None):
        """Load an item for editing, or None for new-item mode."""
        self._item_id = item.get("id") if item else None
        self._form_state = self._init_form_state(self.config.dialog_columns, item)

    async def _handle_save(self):
        item_data = self._build_item_data(self.config.dialog_columns, self._form_state)

        valid, error_dict = self.data_source.validate(item_data)
        if not valid:
            self._notify(
                f"{error_dict['col_name']} {error_dict['error_value']}: {error_dict['error_msg']}",
                type="warning", timeout=1500,
            )
            return

        if self._item_id is not None:
            result = await self.data_source.update_item(self._item_id, item_data)
            if result:
                self._notify(_("Item updated"), type="positive")
        else:
            result = await self.data_source.create_item(item_data)
            if result:
                self._notify(_("Item created"), type="positive")

        if result and self.on_saved:
            self.on_saved(result)

    def _handle_cancel(self):
        if self.on_cancel:
            self.on_cancel()

    @ui.refreshable_method
    async def build(self):
        with html.div().classes("rdm-card rdm-edit-card rdm-component"):
            with html.div().classes("rdm-card-body"):
                for col in self.config.dialog_columns:
                    build_form_field(col, self._form_state)

            with html.div().classes("rdm-edit-actions"):
                with html.button().classes("rdm-btn rdm-btn-primary").on(
                    "click", self._handle_save
                ):
                    html.span(_("Save") if not self.is_new else _("Add"))
                with html.button().classes("rdm-btn rdm-btn-secondary").on(
                    "click", self._handle_cancel
                ):
                    html.span(_("Cancel"))
