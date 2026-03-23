"""
RDM (Reactive Database Management) components for NiceGUI.

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
"""
from pathlib import Path
from nicegui import ui

from .base import ClientComponent, RdmComponent, Column, TableConfig, RowAction, confirm_dialog
from .i18n import _, none_as_text, set_language
from .protocol import RdmDataSource
from ..store import StoreEvent

# Table components
from .table import DataTable
from .list import ListTable
from .selection import SelectionTable
from .edit_dialog import EditDialog
from .dialog import Dialog
from .tabs import Tabs
from .detail import DetailCard
from .edit_card import EditCard
from .view_stack import ViewStack
from .wizard import WizardStep, StepWizard


def rdm_init(language: str | None = None):
    """Initialize RDM module - styles and optional language.

    Loads Bootstrap icons CDN and ng_rdm.css stylesheet.
    Must be called once per page render.

    Args:
        language: Optional language code (e.g., 'nl', 'en').
                  If provided, sets the i18n language for RDM components.
    """
    if language:
        set_language(language)

    # Bootstrap icons CDN
    ui.add_head_html(
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">'
    )

    # Load ng_rdm.css (design system)
    css_path = Path(__file__).parent / 'ng_rdm.css'
    ui.add_css(css_path)


__all__ = [
    # Protocol and events
    'RdmDataSource',
    'StoreEvent',

    # Base classes
    'ClientComponent',
    'RdmComponent',
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

    # Page initialization
    'rdm_init',
    'set_language',
]
