"""
RDM (Reactive Data Management) components for NiceGUI.

Component names:
- ActionButtonTable - table with action buttons per row (edit/delete/custom)
- ListTable - read-only table with clickable rows
- SelectionTable - table with checkbox multi-select
- EditDialog - modal dialog for creating/editing items
- EditCard - in-place editing form
- Dialog - positioned card overlay
- Tabs - div-based tab switcher
- DetailCard - display-only detail view with inline actions
- ViewStack - list/detail/edit navigation
- StepWizard - multi-step form wizard
"""
from pathlib import Path
from nicegui import ui

from .base import RdmComponent, ObservableRdmComponent, ObservableRdmTable, Column, TableConfig, FormConfig, RowAction, confirm_dialog
from .i18n import _, none_as_text, set_language, set_translations
from .protocol import RdmDataSource
from ..store import StoreEvent

# Concrete widget components
from .widgets import (
    ActionButtonTable, ListTable, SelectionTable,
    Dialog, Tabs, DetailCard, EditCard, EditDialog,
    ViewStack, WizardStep, StepWizard,
    Button, IconButton, Row, Col, Separator,
)


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
        extra_css: Optional CSS string | file to add (in addition to ng_rdm.css).
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
    'ObservableRdmTable',
    'Column',
    'TableConfig',
    'FormConfig',
    'RowAction',
    'confirm_dialog',
    'none_as_text',

    # Core components
    'ActionButtonTable',
    'ListTable',
    'SelectionTable',
    'Dialog',
    'Tabs',
    'DetailCard',
    'EditCard',
    'EditDialog',
    'ViewStack',
    'WizardStep',
    'StepWizard',
    'Button',
    'IconButton',
    'Row',
    'Col',
    'Separator',

    # Page initialization
    'rdm_init',
    'set_language',
    'set_translations',
]
