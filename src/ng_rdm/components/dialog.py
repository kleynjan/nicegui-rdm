"""
Dialog - Positioned card overlay, alternative to ui.dialog.

Uses rdm-* CSS classes for consistent styling.
Positions the card at a fixed location (default: top center),
which can feel more natural in master/detail layouts.

Usage:
    with Dialog() as dlg:
        ui.label("Dialog content")
        with dlg.actions():
            ui.button("Save", on_click=handle_save)
            ui.button("Cancel", on_click=dlg.close)
    dlg.open()
"""
from contextlib import contextmanager

from nicegui import html, ui


class Dialog:
    """Positioned card overlay with backdrop.

    Uses native HTML elements with rdm-* CSS classes.
    Unlike ui.dialog which centers content, this positions the card
    at a fixed location for a more app-like feel.
    """

    def __init__(self, dialog_class: str = "", large: bool = False):
        self._client = ui.context.client
        self.dialog_class = dialog_class
        self.large = large
        self._backdrop_div = None
        self._dialog_div = None
        self._body_div = None
        self._keyboard = None
        self._is_open = False

    def __enter__(self):
        """Enter context manager - create dialog structure."""
        # Backdrop (click to close) - contains the dialog
        self._backdrop_div = html.div().classes('rdm-dialog-backdrop rdm-component')
        self._backdrop_div.on('click', self._on_backdrop_click)
        self._backdrop_div.style('display: none')
        self._backdrop_div.__enter__()

        # Dialog container INSIDE the backdrop
        size_class = "rdm-dialog-lg" if self.large else ""
        self._dialog_div = html.div().classes(f'rdm-dialog {size_class} {self.dialog_class}'.strip())
        # Prevent clicks on dialog from closing it (stop propagation via JS)
        self._dialog_div.on('click', lambda _: None, ['stop'])
        self._dialog_div.__enter__()

        # Body section for content
        self._body_div = html.div().classes('rdm-dialog-body')
        self._body_div.__enter__()

        # Keyboard handler for ESC - created once, toggled active on open/close
        self._keyboard = ui.keyboard(on_key=self._on_key, active=False)

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

    def _on_backdrop_click(self, e):
        """Handle backdrop click - close only if click is on backdrop itself."""
        self.close()

    def _on_key(self, e):
        """Handle keyboard events - ESC to close."""
        if e.action.keydown and e.key.name == 'Escape' and self._is_open:
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
        if self._backdrop_div:
            self._backdrop_div.style('display: flex')
            self._is_open = True
            if self._keyboard:
                self._keyboard.active = True

    def close(self):
        """Hide the dialog."""
        if self._backdrop_div:
            self._backdrop_div.style('display: none')
            self._is_open = False
            if self._keyboard:
                self._keyboard.active = False
