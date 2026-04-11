"""
Shared form field builder for dialog, modal table, and edit card.
"""
from typing import Any

from nicegui import ui

from .base import Column

# Display-only types that should not be rendered as form fields
DISPLAY_ONLY_TYPES = {ui.badge, ui.label, ui.html, ui.markdown}

# Custom parameters used for display rendering, not widget construction
DISPLAY_PARAMS = {"color_map"}


def build_cell_field(col: Column, state: dict) -> ui.element | None:
    """Build a compact, label-less editable widget bound to state[col.name].

    For use inside table cells where Quasar's form-field chrome (floating label,
    hint line) is not wanted. Applies `dense flat` props and the `rdm-cell-input`
    class. Returns None for display-only column types.
    """
    ui_type = col.ui_type or ui.input
    if ui_type in DISPLAY_ONLY_TYPES:
        return None

    filtered_parms = {k: v for k, v in col.parms.items() if k not in DISPLAY_PARAMS}
    el = ui_type(**filtered_parms).bind_value(state, col.name)
    el.classes("rdm-cell-input")
    combined_props = f"dense flat {col.props or ''}".strip()
    el.props(combined_props)
    if ui_type == ui.select:
        el.props('popup-content-style="z-index: 6100"')
    return el


def build_form_field(col: Column, state: dict) -> ui.element | None:
    """Build a single form field from a Column config, bound to state[col.name].

    Returns the created UI element, or None if the column type is display-only.
    """
    ui_type = col.ui_type or ui.input

    # Skip display-only column types (badge, label, etc.)
    if ui_type in DISPLAY_ONLY_TYPES:
        return None

    label = col.label or col.name
    kwargs: dict[str, Any] = {}

    if ui_type in (ui.input, ui.number, ui.textarea):
        kwargs["label"] = label
        if col.placeholder:
            kwargs["placeholder"] = col.placeholder
    elif ui_type == ui.checkbox:
        kwargs["text"] = label
    elif ui_type == ui.select:
        kwargs["label"] = label

    # Filter out display-only parameters before passing to widget
    filtered_parms = {k: v for k, v in col.parms.items() if k not in DISPLAY_PARAMS}
    kwargs.update(filtered_parms)

    el = ui_type(**kwargs).bind_value(state, col.name)
    el.classes("form-input")
    if col.props:
        el.props(col.props)
    if ui_type == ui.select:
        el.props('popup-content-style="z-index: 6100"')

    return el
