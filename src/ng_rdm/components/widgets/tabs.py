"""
Tabs - div-based tab switcher.

Uses rdm-* CSS classes for consistent styling.
"""
from typing import Awaitable, Callable

from nicegui import html, ui


class Tabs:
    """Tab bar + panel renderer using native HTML elements.

    All panels are rendered upfront; visibility is toggled via NiceGUI bindings,
    avoiding full DOM rebuilds on tab switch.

    Usage:
        tabs = Tabs(state=ui_state['tabs'], tabs=[
            ("guests", "Guests", render_guests),
            ("admins", "Admins", render_admins),
        ])
        await tabs.build()
    """

    def __init__(
        self,
        state: dict,
        tabs: list[tuple[str, str, Callable[[], Awaitable[None]]]],
        # default: str | None = None,
    ):
        self.state = state
        self.tabs = tabs
        self.state.setdefault("active", tabs[0][0])

    def _select(self, key: str):
        self.state["active"] = key
        self._build_tabbar.refresh()  # type: ignore[attr-defined]

    @ui.refreshable_method
    def _build_tabbar(self):
        with html.div().classes("rdm-tabs rdm-component"):
            for key, label, _ in self.tabs:
                cls = "rdm-tab rdm-active" if self.state["active"] == key else "rdm-tab"
                with html.button().classes(cls).on("click", lambda _, k=key: self._select(k)):
                    html.span(label)

    async def build(self):
        self._build_tabbar()
        for key, _, render in self.tabs:
            panel = html.div().classes("rdm-tab-panel")
            panel.bind_visibility_from(self.state, "active", backward=lambda v, k=key: v == k)
            with panel:
                await render()
