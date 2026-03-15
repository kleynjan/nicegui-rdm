"""
CRUD components for data management.
"""
from pathlib import Path
from nicegui import ui

from .base import CrudComponent, StoreComponent, Column, TableConfig, RowAction, confirm_dialog
from .i18n import none_as_text
from .dialog import CrudDialog
from .detail import DetailCard
from .edit_card import EditCard
from .navigate import NavigateTable
from .tabs import CrudTabs
from .view_stack import ViewStack
from .wizard import WizardStep, StepWizard
from .checkbox import CheckboxTable
from .table import (
    create_crud_table,
    CrudTable,
    DirectEditTable,
    ExplicitEditTable,
)
from .action import ActionButtonTable
from .select import SelectTable


def page_init():
    """
    Initialize page styles for CRUD module.
    Loads Bootstrap icons and crud.css. Must be called per page render.
    """
    # Bootstrap icons CDN
    ui.add_head_html(
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">'
    )

    # Load crud.css
    css_path = Path(__file__).parent / 'crud.css'
    ui.add_css(css_path)

__all__ = [
    'CrudComponent',
    'StoreComponent',
    'none_as_text',
    'CrudDialog',
    'DetailCard',
    'EditCard',
    'ViewStack',
    'WizardStep',
    'StepWizard',
    'CheckboxTable',
    'create_crud_table',
    'CrudTable',
    'DirectEditTable',
    'ExplicitEditTable',
    'ActionButtonTable',
    'NavigateTable',
    'CrudTabs',
    'SelectTable',
    'Column',
    'TableConfig',
    'RowAction',
    'confirm_dialog',
    'page_init',
]
