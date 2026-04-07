"""
EditDialog - Modal dialog for editing or creating a store item.

Renders form columns inside a Dialog overlay.
Used for CRUD operations triggered from tables or other components.
"""
from typing import Any, Callable

from nicegui import ui

from ..i18n import _
from ..base import RdmComponent, FormConfig
from .button import Button
from .dialog import Dialog
from ..fields import build_form_field
from ..protocol import RdmDataSource


class EditDialog(RdmComponent):
    """Modal dialog for editing or creating a store item.

    Args:
        state: Shared state dict. Keys: 'item_id', 'form', 'dialog'.
        data_source: RdmDataSource (typically a Store)
        config: FormConfig with column definitions
        on_saved: Callback when item is saved, receives the saved item
    """

    def __init__(
        self,
        data_source: RdmDataSource,
        config: FormConfig,
        state: dict | None = None,
        *,
        on_saved: Callable[[dict], None] | None = None,
    ):
        super().__init__(data_source)
        self.state = state if state is not None else {}
        self.state.setdefault("item_id", None)
        self.state.setdefault("form", {})
        self.state.setdefault("dialog", {})
        self.config = config
        self.on_saved = on_saved
        self._dlg: Dialog | None = None
        self._dialog_content: Any = None

    @property
    def is_new(self) -> bool:
        return self.state["item_id"] is None

    def open_for_new(self):
        """Open dialog for creating a new item."""
        self.state["item_id"] = None
        self.state["form"] = self._init_form_state(self.config.columns)
        self._show()

    def open_for_edit(self, item: dict):
        """Open dialog for editing an existing item."""
        self.state["item_id"] = item.get("id")
        self.state["form"] = self._init_form_state(self.config.columns, item)
        self._show()

    def _get_title(self) -> str:
        fc = self.config
        return (
            fc.title_edit if not self.is_new else fc.title_add
        ) or (_("Edit") if not self.is_new else _("Add"))

    def _show(self):
        """Show the dialog, creating it lazily on first use."""
        if self._dlg is None:
            self._build_dialog()
        else:
            self._dialog_content.refresh()
        assert self._dlg is not None
        self.state["dialog"]["title"] = self._get_title()
        self._dlg.open()

    def _build_dialog(self):
        """Build the dialog structure once."""
        fc = self.config
        with Dialog(state=self.state["dialog"], title=self._get_title(), dialog_class=fc.dialog_class or "") as self._dlg:
            @ui.refreshable
            def _content():
                # Form fields
                for col in fc.columns:
                    build_form_field(col, self.state["form"])

            self._dialog_content = _content
            _content()

            # Footer - action buttons (outside refreshable for stability)
            with self._dlg.actions():
                Button(_("Save"), on_click=self._handle_save)
                Button(_("Cancel"), color="secondary", on_click=self._dlg.close)

    async def _handle_save(self):
        """Handle save button click in dialog."""
        item_data = self._build_item_data(self.config.columns, self.state["form"])

        # Validate
        (valid, _) = self._validate(item_data)
        if not valid:
            return

        if not self.is_new and self.state["item_id"] is not None:
            result = await self._update(self.state["item_id"], item_data)
        else:
            result = await self._validate_and_create(item_data)

        if result:
            if self._dlg:
                self._dlg.close()
            if self.on_saved:
                self.on_saved(result)
