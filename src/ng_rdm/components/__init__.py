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

from .base import RdmComponent, ObservableRdmComponent, Column, TableConfig, RowAction, confirm_dialog
from .i18n import _, none_as_text, set_language, set_translations
from .protocol import RdmDataSource
from ..store import StoreEvent

# Table components
from .data_table import DataTable
from .list_table import ListTable
from .selection import SelectionTable
from .edit_dialog import EditDialog
from .dialog import Dialog
from .tabs import Tabs
from .detail import DetailCard
from .edit_card import EditCard
from .view_stack import ViewStack
from .wizard import WizardStep, StepWizard
from .button import Button, IconButton


def rdm_init(
    custom_translations: dict[str, dict[str, str]] | None = None,
    extra_css: str | None = None,
):
    """Initialize RDM module - styles and optional customizations.

    Loads Bootstrap icons CDN and ng_rdm.css stylesheet.
    Must be called once per page render.

    Args:
        custom_translations: Optional dict to update/extend built-in translations.
                             Structure: {'lang_code': {'key': 'translation', ...}, ...}
        extra_css: Optional CSS string to add after ng_rdm.css.
    """
    if custom_translations:
        set_translations(custom_translations)

    # Bootstrap icons CDN
    ui.add_head_html(
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">'
    )

    # Load ng_rdm.css (design system)
    css_path = Path(__file__).parent / 'ng_rdm.css'
    ui.add_css(css_path)

    # Extra CSS (after native styles)
    if extra_css:
        ui.add_css(extra_css)

    # enable this to add an observer/event log at /rdm-debug
    from ..debug import enable_debug_page
    enable_debug_page()  # Optional: enable debug page for event stream visualization


__all__ = [
    # Protocol and events
    'RdmDataSource',
    'StoreEvent',

    # Base classes
    'RdmComponent',
    'ObservableRdmComponent',
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
    'Button',
    'IconButton',

    # Page initialization
    'rdm_init',
    'set_language',
    'set_translations',
]
