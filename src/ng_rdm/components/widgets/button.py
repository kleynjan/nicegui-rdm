"""
Button helpers for RDM - providing clean API for icon buttons with Bootstrap Icons.

For regular buttons, use ui.button() directly with rdm-btn-* classes:
    ui.button("Save", on_click=fn).classes("rdm-btn-primary")
    ui.button("Cancel", on_click=fn).classes("rdm-btn-secondary")

For icon-only buttons, use the icon_button() helper:
    icon_button("pencil", on_click=edit_handler, tooltip="Edit")
"""
from typing import Any, Callable

from nicegui import ui


def icon_button(
    icon: str,
    on_click: Callable[..., Any] | None = None,
    tooltip: str | None = None,
) -> ui.button:
    """Create an icon-only button with Bootstrap Icon.

    Args:
        icon: Bootstrap icon name without "bi-" prefix (e.g., "pencil", "trash", "x")
        on_click: Click handler (sync or async function)
        tooltip: Hover tooltip text (optional)

    Returns:
        The ui.button element for further customization.

    Example:
        icon_button("pencil", on_click=edit_handler, tooltip="Edit")
        icon_button("trash", on_click=delete_handler, tooltip="Delete")
    """
    btn = ui.button(on_click=on_click).classes("rdm-btn-icon")
    if tooltip:
        btn.props(f'title="{tooltip}"')
    with btn:
        ui.html(f'<i class="bi bi-{icon}"></i>')
    return btn
