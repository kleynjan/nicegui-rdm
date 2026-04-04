"""
Test Buttons - Visual comparison of html.button vs Button subclass.

Side-by-side rendering of every button variant to iterate on CSS until
ui.button (Quasar) is pixel-identical to html.button (reference).

Run:  python -m ng_rdm.examples.test_buttons
Open: http://localhost:8090
"""
from nicegui import ui, html

from ng_rdm.components import rdm_init
from ng_rdm.components.widgets.button import Button, IconButton

OUTLINE_CSS = """
.debug-outlines .q-btn          { outline: 2px solid limegreen !important; }
.debug-outlines .q-btn__wrapper { outline: 2px solid red !important; }
.debug-outlines .q-btn__content { outline: 2px solid blue !important; }
.debug-outlines .rdm-btn        { outline: 2px solid orange !important; }
"""

SECTION = 'margin-bottom: 28px;'
VARIANT_LABEL = 'font-size: 11px; color: #888; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px;'
COL_HEAD = 'font-size: 12px; color: #999; padding-bottom: 6px; border-bottom: 1px solid #eee; margin-bottom: 10px;'
GRID = 'display: grid; grid-template-columns: 1fr 1fr; gap: 24px;'
FLEX = 'display: flex; gap: 8px; flex-wrap: wrap; align-items: center;'


def variant_label(text: str) -> None:
    ui.label(text).style(VARIANT_LABEL)


def col_head(text: str) -> None:
    ui.label(text).style(COL_HEAD)


def h_row() -> ui.element:
    return ui.element('div').style(FLEX)


def h_btn(label: str, variant: str, small: bool = False, disabled: bool = False) -> None:
    classes = f'rdm-btn rdm-btn-{variant}' + (' rdm-btn-sm' if small else '')
    btn = html.button().classes(classes)
    if disabled:
        btn.props('disabled')
    with btn:
        html.span(label)


def h_icon_btn(icon: str, disabled: bool = False) -> None:
    btn = html.button().classes('rdm-btn rdm-btn-icon')
    if disabled:
        btn.props('disabled')
    with btn:
        html.i().classes(f'bi bi-{icon}')


@ui.page('/')
def page() -> None:
    rdm_init()
    ui.add_css(OUTLINE_CSS)

    with ui.element('div').style('padding: 32px; max-width: 920px; margin: 0 auto;'):
        # Header
        with ui.element('div').style('display: flex; align-items: center; gap: 16px; margin-bottom: 8px;'):
            ui.label('Button Comparison').style('font-size: 20px; font-weight: 700;')
        with ui.element('div').style('display: flex; align-items: center; gap: 12px; margin-bottom: 28px;'):
            ui.label('Left: html.button (reference)   Right: Button subclass (target)').style('font-size: 13px; color: #888;')

        container = ui.element('div')
        Button('Toggle outlines', color='secondary',
               on_click=lambda: container.classes(toggle='debug-outlines')).style('margin-bottom: 24px;')

        with container:

            # ------------------------------------------------------------------
            # Primary
            # ------------------------------------------------------------------
            with ui.element('div').style(SECTION):
                variant_label('Primary')
                with ui.element('div').style(GRID):
                    with ui.element('div'):
                        col_head('html.button')
                        with h_row():
                            h_btn('Save', 'primary')
                            h_btn('Save', 'primary', disabled=True)
                            with html.button().classes('rdm-btn rdm-btn-primary'):
                                html.i().classes('bi bi-pencil')
                                html.span('Edit')
                    with ui.element('div'):
                        col_head('Button subclass')
                        with h_row():
                            Button('Save')
                            Button('Save').props('disable')
                            with Button('Edit'):
                                ui.html('<i class="bi bi-pencil"></i>')

            # ------------------------------------------------------------------
            # Secondary
            # ------------------------------------------------------------------
            with ui.element('div').style(SECTION):
                variant_label('Secondary')
                with ui.element('div').style(GRID):
                    with ui.element('div'):
                        col_head('html.button')
                        with h_row():
                            h_btn('Cancel', 'secondary')
                            h_btn('Cancel', 'secondary', disabled=True)
                    with ui.element('div'):
                        col_head('Button subclass')
                        with h_row():
                            Button('Cancel', color='secondary')
                            Button('Cancel', color='secondary').props('disable')

            # ------------------------------------------------------------------
            # Danger / Success / Warning
            # ------------------------------------------------------------------
            with ui.element('div').style(SECTION):
                variant_label('Danger / Success / Warning')
                with ui.element('div').style(GRID):
                    with ui.element('div'):
                        col_head('html.button')
                        with h_row():
                            h_btn('Delete', 'danger')
                            h_btn('Confirm', 'success')
                            h_btn('Caution', 'warning')
                    with ui.element('div'):
                        col_head('Button subclass')
                        with h_row():
                            Button('Delete', color='danger')
                            Button('Confirm', color='success')
                            Button('Caution', color='warning')

            # ------------------------------------------------------------------
            # Text
            # ------------------------------------------------------------------
            with ui.element('div').style(SECTION):
                variant_label('Text')
                with ui.element('div').style(GRID):
                    with ui.element('div'):
                        col_head('html.button')
                        with h_row():
                            h_btn('Learn more', 'text')
                    with ui.element('div'):
                        col_head('Button subclass')
                        with h_row():
                            Button('Learn more', color='text')

            # ------------------------------------------------------------------
            # Icon-only
            # ------------------------------------------------------------------
            with ui.element('div').style(SECTION):
                variant_label('Icon-only')
                with ui.element('div').style(GRID):
                    with ui.element('div'):
                        col_head('html.button')
                        with h_row():
                            h_icon_btn('pencil')
                            h_icon_btn('trash')
                            h_icon_btn('x-lg')
                            h_icon_btn('pencil', disabled=True)
                    with ui.element('div'):
                        col_head('Button subclass')
                        with h_row():
                            IconButton('pencil')
                            IconButton('trash')
                            IconButton('x-lg')
                            IconButton('pencil').props('disable')

            # ------------------------------------------------------------------
            # Small (rdm-btn-sm)
            # ------------------------------------------------------------------
            with ui.element('div').style(SECTION):
                variant_label('Small (rdm-btn-sm)')
                with ui.element('div').style(GRID):
                    with ui.element('div'):
                        col_head('html.button')
                        with h_row():
                            h_btn('Edit', 'primary', small=True)
                            h_btn('Cancel', 'secondary', small=True)
                    with ui.element('div'):
                        col_head('Button subclass')
                        with h_row():
                            Button('Edit').classes('rdm-btn-sm')
                            Button('Cancel', color='secondary').classes('rdm-btn-sm')

            # ------------------------------------------------------------------
            # Composite: table action row
            # ------------------------------------------------------------------
            with ui.element('div').style(SECTION):
                variant_label('Composite: Table action row')
                with ui.element('div').style(GRID):
                    with ui.element('div'):
                        col_head('html.button')
                        with h_row():
                            h_icon_btn('pencil')
                            h_icon_btn('trash')
                    with ui.element('div'):
                        col_head('Button subclass')
                        with h_row():
                            IconButton('pencil', tooltip='Edit')
                            IconButton('trash', tooltip='Delete')

            # ------------------------------------------------------------------
            # Composite: dialog footer
            # ------------------------------------------------------------------
            with ui.element('div').style(SECTION):
                variant_label('Composite: Dialog footer (Save + Cancel)')
                with ui.element('div').style(GRID):
                    with ui.element('div'):
                        col_head('html.button')
                        with h_row():
                            h_btn('Save', 'primary')
                            h_btn('Cancel', 'secondary')
                    with ui.element('div'):
                        col_head('Button subclass')
                        with h_row():
                            Button('Save')
                            Button('Cancel', color='secondary')

            # ------------------------------------------------------------------
            # Composite: toolbar add button
            # ------------------------------------------------------------------
            with ui.element('div').style(SECTION):
                variant_label('Composite: Toolbar add button')
                with ui.element('div').style(GRID):
                    with ui.element('div'):
                        col_head('html.button')
                        with h_row():
                            with html.button().classes('rdm-btn rdm-btn-primary'):
                                html.span('+ Add new')
                    with ui.element('div'):
                        col_head('Button subclass')
                        with h_row():
                            Button('+ Add new')


ui.run(title='Button Comparison', port=8090, show=False)
