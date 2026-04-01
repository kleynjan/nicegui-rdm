"""
Layout primitives — Row, Col, Separator.

Thin wrappers around html.div / html.hr that apply flexbox layout
without Quasar wrappers. Follow the same pattern as Button.
"""
from nicegui import html


class Row:
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

    def __init__(
        self,
        *,
        gap: str = "1rem",
        align: str = "center",
        classes: str = "",
        style: str = "",
    ):
        base = f"display:flex; align-items:{align}; gap:{gap}"
        combined = f"{base}; {style}" if style else base
        self.element = html.div().classes(f"rdm-row {classes}".strip()).style(combined)

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


class Col:
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

    def __init__(
        self,
        *,
        gap: str = "",
        classes: str = "",
        style: str = "",
    ):
        base = "display:flex; flex-direction:column"
        if gap:
            base += f"; gap:{gap}"
        combined = f"{base}; {style}" if style else base
        self.element = html.div().classes(f"rdm-col {classes}".strip()).style(combined)

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


class Separator:
    """Horizontal rule using rdm-separator styling.

    Example:
        Separator()
    """

    def __init__(self):
        html.hr().classes("rdm-separator").style("border: none")
