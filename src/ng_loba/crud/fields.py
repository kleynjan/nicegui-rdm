"""
Shared form field builder for dialog, modal table, and edit card.
"""
from typing import Any

from nicegui import ui

from .base import Column


def build_form_field(col: Column, state: dict) -> ui.element:
    """Build a single form field from a Column config, bound to state[col.name].

    Returns the created UI element for further customization if needed.
    """
    label = col.label or col.name
    ui_type = col.ui_type or ui.input

    kwargs: dict[str, Any] = {}

    if ui_type in (ui.input, ui.number, ui.textarea):
        kwargs["label"] = label
        if col.placeholder:
            kwargs["placeholder"] = col.placeholder
    elif ui_type == ui.checkbox:
        kwargs["text"] = label
    elif ui_type == ui.select:
        kwargs["label"] = label

    kwargs.update(col.parms)

    el = ui_type(**kwargs).bind_value(state, col.name)
    el.classes("form-input")
    if col.props:
        el.props(col.props)
    if ui_type == ui.select:
        el.props('popup-content-style="z-index: 6100"')

    return el
