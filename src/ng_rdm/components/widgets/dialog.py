"""
Dialog - Positioned card overlay, alternative to ui.dialog.

Uses rdm-* CSS classes for consistent styling.
Positions the card at a fixed location (default: top center),
which can feel more natural in master/detail layouts.

Usage:
    # Simple dialog with auto-generated header
    with Dialog(state=ui_state['dialog'], title="Edit Item") as dlg:
        ui.input("Name")
        with dlg.actions():
            ui.button("Save", on_click=handle_save)
            ui.button("Cancel", on_click=dlg.close)
    dlg.open()

    # Dialog without title (manual header or headerless)
    with Dialog(state=ui_state['dialog']) as dlg:
        ui.label("Dialog content")
        with dlg.actions():
            ui.button("OK", on_click=dlg.close)
    dlg.open()
"""
from contextlib import contextmanager
from typing import Callable

from nicegui import context, html, ui

from .button import IconButton


class Dialog:
    """Positioned card overlay with backdrop.

    Uses native HTML elements with rdm-* CSS classes.
    Unlike ui.dialog which centers content, this positions the card
    at a fixed location for a more app-like feel.

    Args:
        title: Optional title for auto-generated header with close button
        dialog_class: Additional CSS classes for the dialog container
        on_close: Optional callback when dialog is closed
    """

    def __init__(
        self,
        state: dict | None = None,
        title: str | None = None,
        dialog_class: str = "",
        on_close: Callable[[], None] | None = None,
    ):
        self._client = ui.context.client
        self.state = state if state is not None else {}
        self.state.setdefault("is_open", False)
        self.title = title
        self.dialog_class = dialog_class
        self.on_close = on_close
        self._backdrop_div = None
        self._dialog_div = None
        self._body_div = None
        self._keyboard = None

    def __enter__(self):
        """Enter context manager - create dialog structure.

        Attaches the backdrop to the client's root layout so the dialog
        DOM survives @ui.refreshable rebuilds regardless of call site.
        """
        # Attach backdrop to client root layout (escapes any refreshable zone)
        layout = context.client.layout
        layout.__enter__()
        self._backdrop_div = html.div().classes('rdm-dialog-backdrop rdm-component')
        self._backdrop_div.bind_visibility_from(self.state, 'is_open')
        layout.__exit__(None, None, None)

        self._backdrop_div.__enter__()

        # Dialog container INSIDE the backdrop
        self._dialog_div = html.div().classes(f'rdm-dialog {self.dialog_class}'.strip())
        # Prevent clicks on dialog from closing it (stop propagation via JS)
        self._dialog_div.on('click', lambda _: None, ['stop'])
        self._dialog_div.__enter__()

        # Header section (if title provided)
        if self.title:
            self._header_div = html.div().classes('rdm-dialog-header')
            with self._header_div:
                ui.label(self.title).classes('rdm-dialog-title')
                IconButton("x-lg", on_click=self.close).classes("rdm-dialog-close")

        # Body section for content
        self._body_div = html.div().classes('rdm-dialog-body')
        self._body_div.__enter__()

        # Keyboard handler for ESC - created once, toggled active on open/close
        # ignore=[] ensures it works even when an input/button is focused
        self._keyboard = ui.keyboard(on_key=self._on_key, active=False, ignore=[])

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        if self._body_div:
            self._body_div.__exit__(exc_type, exc_val, exc_tb)
        if self._dialog_div:
            self._dialog_div.__exit__(exc_type, exc_val, exc_tb)
        if self._backdrop_div:
            self._backdrop_div.__exit__(exc_type, exc_val, exc_tb)
        return False

    def _on_key(self, e):
        """Handle keyboard events - ESC to close."""
        if e.action.keydown and e.key == 'Escape' and self.state.get('is_open'):
            self.close()

    @contextmanager
    def actions(self):
        """Context manager for dialog action buttons row."""
        if self._dialog_div is None:
            raise RuntimeError("actions() must be called within Dialog context")

        with self._dialog_div:
            footer = html.div().classes('rdm-dialog-footer')
            with footer:
                yield

    def open(self):
        """Show the dialog."""
        self.state['is_open'] = True
        if self._keyboard:
            self._keyboard.active = True

    def close(self):
        """Hide the dialog."""
        self.state['is_open'] = False
        if self._keyboard:
            self._keyboard.active = False
        if self.on_close:
            self.on_close()

    def _notify(self, message: str, **kwargs) -> None:
        """Show notification safely from async context."""
        with self._client:
            ui.notification(message, position="bottom-left", timeout=3, **kwargs)
