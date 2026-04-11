"""
RDM button components - thin wrappers around ui.button with RDM styling.

Button and IconButton follow the ui.button API but map `color` to
rdm-btn-{color} CSS classes instead of Quasar's color system.

Usage:
    Button("Save")                           # primary (default)
    Button("Cancel", color="secondary")
    Button("Delete", color="danger")
    IconButton("pencil", on_click=edit_fn, tooltip="Edit")
"""
from typing import Any, Callable

from nicegui import ui


class Button(ui.button, default_props='flat unelevated no-caps'):
    """RDM-styled button. `color` maps to rdm-btn-{color} CSS class."""

    def __init__(
        self,
        text: str = '',
        *,
        on_click: Callable[..., Any] | None = None,
        color: str | None = 'primary',
        **kwargs: Any,
    ) -> None:
        super().__init__(text, on_click=on_click, color=None, **kwargs)
        if color:
            self.classes(f'rdm-btn-{color}')


class IconButton(ui.button, default_props='flat unelevated no-caps'):
    """RDM-styled icon-only button using Bootstrap Icons."""

    def __init__(
        self,
        icon: str,
        *,
        on_click: Callable[..., Any] | None = None,
        color: str | None = 'primary',
        tooltip: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(on_click=on_click, color=None, **kwargs)
        self.classes('rdm-btn-icon')
        if tooltip:
            self.props(f'title="{tooltip}"')
        with self:
            ui.html(f'<i class="bi bi-{icon} rdm-btn-icon-{color}"></i>', sanitize=False)


class Icon(ui.icon):
    """RDM-styled icon using Bootstrap Icons."""

    def __init__(
        self,
        icon: str,
        *,
        on_click: Callable[..., Any] | None = None,
        color: str | None = 'primary',
        tooltip: str | None = None,
    ) -> None:
        super().__init__(name='', color=None)
        self.classes('rdm-icon')
        if tooltip:
            self.props(f'title="{tooltip}"')
        if on_click:
            self.on('click', on_click)
        with self:
            ui.html(f'<i class="bi bi-{icon} rdm-icon-{color}"></i>', sanitize=False)
