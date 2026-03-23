"""
Button - RDM-styled button component.

Provides a clean API for creating buttons with the rdm design system,
without requiring knowledge of CSS class names.
"""
from typing import Any, Callable

from nicegui import html


class Button:
    """RDM-styled button using native HTML with design system classes.

    Creates a button with consistent rdm styling. Supports multiple variants,
    optional icons, and size options.

    Args:
        label: Button text
        on_click: Click handler (sync or async function)
        variant: Style variant - "primary", "secondary", "success", "danger",
                 "warning", "text" (default: "primary")
        icon: Bootstrap icon name without "bi-" prefix (e.g., "check", "x", "plus")
        size: Size - "default" or "sm" (default: "default")
        disabled: Whether button is disabled (default: False)

    Example:
        Button("Save", on_click=save_handler)
        Button("Cancel", on_click=cancel, variant="secondary")
        Button("Delete", on_click=delete, variant="danger", icon="trash")
        Button("Add", on_click=add, size="sm")
    """

    def __init__(
        self,
        label: str,
        on_click: Callable[..., Any] | None = None,
        variant: str = "primary",
        icon: str | None = None,
        size: str = "default",
        disabled: bool = False,
    ):
        # Build CSS classes
        classes = ["rdm-btn", f"rdm-btn-{variant}"]
        if size == "sm":
            classes.append("rdm-btn-sm")

        # Create button element
        self.element = html.button().classes(" ".join(classes))

        if disabled:
            self.element.props("disabled")

        if on_click:
            self.element.on("click", on_click)

        # Content: icon + label
        with self.element:
            if icon:
                html.i().classes(f"bi bi-{icon}")
            html.span(label)

    def classes(self, *args, **kwargs):
        """Add additional classes to the button."""
        self.element.classes(*args, **kwargs)
        return self

    def props(self, *args, **kwargs):
        """Add additional props to the button."""
        self.element.props(*args, **kwargs)
        return self

    def style(self, *args, **kwargs):
        """Add additional styles to the button."""
        self.element.style(*args, **kwargs)
        return self


class IconButton:
    """RDM-styled icon-only button.

    Creates a minimal icon button without text label.

    Args:
        icon: Bootstrap icon name without "bi-" prefix (e.g., "pencil", "trash", "x")
        on_click: Click handler (sync or async function)
        tooltip: Hover tooltip text (optional)
        disabled: Whether button is disabled (default: False)

    Example:
        IconButton("pencil", on_click=edit_handler, tooltip="Edit")
        IconButton("trash", on_click=delete_handler, tooltip="Delete")
    """

    def __init__(
        self,
        icon: str,
        on_click: Callable[..., Any] | None = None,
        tooltip: str | None = None,
        disabled: bool = False,
    ):
        self.element = html.button().classes("rdm-btn rdm-btn-icon")

        if disabled:
            self.element.props("disabled")

        if tooltip:
            self.element.props(f'title="{tooltip}"')

        if on_click:
            self.element.on("click", on_click)

        with self.element:
            html.i().classes(f"bi bi-{icon}")

    def classes(self, *args, **kwargs):
        """Add additional classes to the button."""
        self.element.classes(*args, **kwargs)
        return self

    def props(self, *args, **kwargs):
        """Add additional props to the button."""
        self.element.props(*args, **kwargs)
        return self

    def style(self, *args, **kwargs):
        """Add additional styles to the button."""
        self.element.style(*args, **kwargs)
        return self
