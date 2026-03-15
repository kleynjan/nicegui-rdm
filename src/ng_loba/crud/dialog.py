"""
CrudDialog - positioned card overlay as dialog replacement.

Provides a cleaner alternative to Quasar's ui.dialog with better control
over positioning and styling.
"""
from contextlib import contextmanager

from nicegui import ui

from .base import CrudComponent


class CrudDialog(CrudComponent):
    """Dialog implemented as a positioned card overlay.

    Usage:
        with CrudDialog() as dlg:
            ui.label("Dialog content")
            with dlg.actions():
                ui.button("Close", on_click=dlg.close)
        dlg.open()
    """

    def __init__(self):
        super().__init__()
        self._backdrop_div = None
        self._container_div = None
        self._card = None
        self._actions_row = None
        self._is_open = False

    def __enter__(self):
        """Enter context manager - create dialog structure."""
        # Backdrop (click to close)
        self._backdrop_div = ui.element('div').classes('crud-dialog-backdrop')
        self._backdrop_div.on('click', self.close)
        self._backdrop_div.style('display: none')

        # Container for positioning
        self._container_div = ui.element('div').classes('crud-dialog-container')
        self._container_div.style('display: none')

        # Card content - start context but keep it open
        self._container_div.__enter__()
        self._card = ui.card().classes('crud-dialog-card')
        self._card.__enter__()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - close card and container contexts."""
        if self._card:
            self._card.__exit__(exc_type, exc_val, exc_tb)
        if self._container_div:
            self._container_div.__exit__(exc_type, exc_val, exc_tb)
        return False

    @contextmanager
    def actions(self):
        """Context manager for dialog action buttons row."""
        if self._card is None:
            raise RuntimeError("actions() must be called within CrudDialog context")

        with self._card:
            self._actions_row = ui.row().classes('crud-dialog-actions')
            with self._actions_row:
                yield

    def open(self):
        """Show the dialog."""
        if self._backdrop_div and self._container_div:
            self._backdrop_div.style('display: block')
            self._container_div.style('display: block')
            self._is_open = True

            # Set up ESC key handler
            ui.keyboard(on_key=lambda e: self.close() if e.key == 'Escape' and self._is_open else None)

    def close(self):
        """Hide the dialog."""
        if self._backdrop_div and self._container_div:
            self._backdrop_div.style('display: none')
            self._container_div.style('display: none')
            self._is_open = False
