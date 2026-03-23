"""
CRUD components for NiceGUI data management.

Component names:
- DataTable - primary editable table with configurable actions (icon/button style)
- ListTable - read-only table with clickable rows
- SelectionTable - table with checkbox multi-select
- EditDialog - standalone modal dialog for add/edit operations
- Dialog - positioned card overlay
- Tabs - div-based tab switcher
- DetailCard - display-only detail view
- EditCard - in-place editing form
- ViewStack - list/detail/edit navigation
- StepWizard - multi-step form wizard

Backwards-compatible aliases:
- ModalEditTable → DataTable
- ActionTable → DataTable
- ActionButtonTable → DataTable
- NavigateTable → ListTable
- CheckboxTable → SelectionTable
- CrudDialog → Dialog
- CrudTabs → Tabs
"""
from pathlib import Path
from nicegui import ui

from .base import CrudComponent, StoreComponent, Column, TableConfig, RowAction, confirm_dialog
from .i18n import _, none_as_text, set_language
from .protocol import CrudDataSource
from ..store import StoreEvent

# Core components
from .table import DataTable, ModalEditTable, ActionButtonTable, ActionTable
from .list import ListTable, NavigateTable
from .selection import SelectionTable, CheckboxTable
from .edit_dialog import EditDialog
from .dialog import Dialog, CrudDialog
from .tabs import Tabs, CrudTabs
from .detail import DetailCard
from .edit_card import EditCard
from .view_stack import ViewStack
from .wizard import WizardStep, StepWizard


def crud_init(language: str | None = None):
    """Initialize CRUD module - styles and optional language.

    Loads Bootstrap icons CDN and nicecrud.css stylesheet.
    Must be called once per page render.

    Args:
        language: Optional language code (e.g., 'nl', 'en').
                  If provided, sets the i18n language for CRUD components.
    """
    if language:
        set_language(language)

    # Bootstrap icons CDN
    ui.add_head_html(
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">'
    )

    # Load nicecrud.css (design system)
    css_path = Path(__file__).parent / 'nicecrud.css'
    ui.add_css(css_path)


# Backwards compatibility alias
page_init = crud_init


__all__ = [
    # Protocol and events
    'CrudDataSource',
    'StoreEvent',

    # Base classes
    'CrudComponent',
    'StoreComponent',
    'Column',
    'TableConfig',
    'RowAction',
    'confirm_dialog',
    'none_as_text',

    # Core components
    'DataTable',
    'ListTable',
    'SelectionTable',
    'EditDialog',
    'Dialog',
    'Tabs',
    'DetailCard',
    'EditCard',
    'ViewStack',
    'WizardStep',
    'StepWizard',

    # Backwards-compatible aliases (deprecated)
    'ModalEditTable',
    'ActionTable',
    'ActionButtonTable',
    'NavigateTable',
    'CheckboxTable',
    'CrudDialog',
    'CrudTabs',

    # Page initialization
    'crud_init',
    'page_init',  # backwards compatibility
    'set_language',
]
