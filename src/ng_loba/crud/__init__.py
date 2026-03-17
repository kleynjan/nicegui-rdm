"""
CRUD components for data management.

New component names (nicecrud):
- DataTable - primary editable table with modal editing
- ListTable - read-only table with clickable rows
- ActionTable - table with edit/delete action buttons
- SelectionTable - table with checkbox multi-select
- Dialog - positioned card overlay
- Tabs - div-based tab switcher

Backwards-compatible aliases:
- ModalEditTable → DataTable
- NavigateTable → ListTable
- ActionButtonTable → ActionTable
- CheckboxTable → SelectionTable
- CrudDialog → Dialog
- CrudTabs → Tabs
"""
from pathlib import Path
from nicegui import ui

from .base import CrudComponent, StoreComponent, Column, TableConfig, RowAction, confirm_dialog
from .i18n import none_as_text

# New component names
from .table import DataTable, ModalEditTable
from .list import ListTable, NavigateTable
from .action_table import ActionTable, ActionButtonTable
from .selection import SelectionTable, CheckboxTable
from .dialog import Dialog, CrudDialog
from .tabs import Tabs, CrudTabs
from .detail import DetailCard
from .edit_card import EditCard
from .view_stack import ViewStack
from .wizard import WizardStep, StepWizard

# Legacy imports for backwards compatibility (deprecated)
from .navigate import NavigateTable as _OldNavigateTable
from .checkbox import CheckboxTable as _OldCheckboxTable
from .action import ActionButtonTable as _OldActionButtonTable


def page_init():
    """
    Initialize page styles for CRUD module.
    Loads Bootstrap icons and nicecrud.css. Must be called per page render.
    """
    # Bootstrap icons CDN
    ui.add_head_html(
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">'
    )

    # Load nicecrud.css (new design system)
    css_path = Path(__file__).parent / 'nicecrud.css'
    ui.add_css(css_path)

    # Also load legacy crud.css for backwards compatibility
    legacy_css_path = Path(__file__).parent / 'crud.css'
    if legacy_css_path.exists():
        ui.add_css(legacy_css_path)


__all__ = [
    # Base classes
    'CrudComponent',
    'StoreComponent',
    'Column',
    'TableConfig',
    'RowAction',
    'confirm_dialog',
    'none_as_text',

    # New component names (preferred)
    'DataTable',
    'ListTable',
    'ActionTable',
    'SelectionTable',
    'Dialog',
    'Tabs',
    'DetailCard',
    'EditCard',
    'ViewStack',
    'WizardStep',
    'StepWizard',

    # Backwards-compatible aliases (deprecated)
    'ModalEditTable',
    'NavigateTable',
    'ActionButtonTable',
    'CheckboxTable',
    'CrudDialog',
    'CrudTabs',

    # Page initialization
    'page_init',
]
