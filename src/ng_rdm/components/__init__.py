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
    Button, Icon, IconButton, RdmLayoutElement, Row, Col, Separator,
)

show_refresh_css = """
/* show refreshable components with a green border animation when they update */
.show-refresh {
  border: 2px solid green;
  animation: borderAnimation 2s forwards;
}
@keyframes borderAnimation {
  0% {
    border: 2px solid green;
  }
  100% {
    border: 2px solid white;
  }
}
"""

def rdm_init(
    custom_translations: dict[str, dict[str, str]] | None = None,
    extra_css: str | Path | None = None,
    timezone: str | None = None,
    show_refresh_transitions: bool = False,
    show_store_event_log: bool = False,
    log_file: str | Path | None = None,
):
    """Initialize RDM module - styles and optional customizations.

    Loads Bootstrap icons CDN and ng_rdm.css stylesheet.
    Must be called once per page render.

    Args:
        custom_translations: Optional dict to update/extend built-in translations.
                             Structure: {'lang_code': {'key': 'translation', ...}, ...}
        extra_css: Optional CSS string | file to add (in addition to ng_rdm.css).
        timezone: Optional timezone string (e.g. 'Europe/Amsterdam'). Default: 'Europe/Amsterdam'.
        show_refresh_transitions: If True, adds a CSS animation to highlight refreshable components when they update.
        show_store_event_log: If True, enables a debug page at /rdm-debug to visualize store events.
        log_file: Optional path. When set, routes ng_rdm, Tortoise ORM and uvicorn logs to this file.
    """

    # Bootstrap icons CDN
    ui.add_head_html(
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">'
    )

    # add ng_rdm.css
    css_path = Path(__file__).parent / 'ng_rdm.css'
    ui.add_css(css_path)

    ui.colors(primary="#3b82f6")  # sync with var(--rdm-primary) in css

    if timezone:
        from ..utils.helpers import configure_timezone
        configure_timezone(timezone)

    if custom_translations:
        set_translations(custom_translations)

    if extra_css:
        ui.add_css(extra_css)

    if show_refresh_transitions:
        ui.add_css(show_refresh_css)

    if show_store_event_log:
        from ..debug import enable_debug_page
        enable_debug_page()  # Optional: enable debug page for event stream visualization

    if log_file:
        from ..utils.logging import _configure_file_logging
        _configure_file_logging(log_file)


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
    'Button',
    'Icon',
    'IconButton',
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
    'RdmLayoutElement',
    'Row',
    'Col',
    'Separator',

    # Page initialization
    'rdm_init',
    'set_language',
    'set_translations',
]
