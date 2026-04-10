"""
Layout primitives — Row, Col, Separator.

Thin wrappers around html.div that apply flexbox layout
without Quasar wrappers. All share RdmLayoutElement as base.
"""
from nicegui import html


class RdmLayoutElement:
    """Base for lightweight layout elements (Row, Col, Separator).

    Handles element creation, CSS classes, inline styles, and context manager protocol.
    Subclasses set _html_tag and _css_class, then call super().__init__().
    """
    _html_tag = html.div
    _css_class: str = ''

    def __init__(self, *, classes: str = '', style: str = ''):
        css = f'{self._css_class} {classes}'.strip()
        self.element = self._html_tag().classes(css)
        if style:
            self.element.style(style)

    def classes(self, c: str):
        self.element.classes(c)
        return self

    def style(self, s: str):
        self.element.style(s)
        return self

    def __enter__(self):
        self.element.__enter__()
        return self

    def __exit__(self, *args):
        return self.element.__exit__(*args)


class Row(RdmLayoutElement):
    """Flex row container using native html.div.

    Args:
        gap: Spacing between children (default: "1rem")
        align: align-items value (default: "center")
        classes: Additional CSS classes
        style: Additional inline styles (appended after flex base styles)

    Example:
        with Row():
            Button("A")
            Button("B")
        with Row(gap="2rem", align="flex-start"):
            ...
    """
    _css_class = 'rdm-row'

    def __init__(self, *, gap: str = '1rem', align: str = 'center', classes: str = '', style: str = ''):
        base = f'display:flex; align-items:{align}; gap:{gap}'
        combined = f'{base}; {style}' if style else base
        super().__init__(classes=classes, style=combined)


class Col(RdmLayoutElement):
    """Flex column container using native html.div.

    Args:
        gap: Spacing between children (default: none)
        classes: Additional CSS classes
        style: Additional inline styles (appended after flex base styles)

    Example:
        with Col(classes="demo-content-column"):
            ...
        with Col(gap="1rem", style="max-width: 56rem; margin: 0 auto"):
            ...
    """
    _css_class = 'rdm-col'

    def __init__(self, *, gap: str = '', classes: str = '', style: str = ''):
        base = 'display:flex; flex-direction:column'
        if gap:
            base += f'; gap:{gap}'
        combined = f'{base}; {style}' if style else base
        super().__init__(classes=classes, style=combined)


class Separator(RdmLayoutElement):
    """Thin horizontal divider using rdm-separator styling.

    Args:
        classes: Additional CSS classes
        style: Additional inline styles

    Example:
        Separator()
        Separator(style="margin: 2rem 0")
    """
    _html_tag = html.div
    _css_class = 'rdm-separator'

    def __init__(self, *, classes: str = '', style: str = ''):
        super().__init__(classes=classes, style=style)
        self.element.props('role=separator')
