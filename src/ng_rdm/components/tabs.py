"""
Tabs - div-based tab switcher.

Uses rdm-* CSS classes for consistent styling.
"""
from typing import Awaitable, Callable

from nicegui import html, ui


class Tabs:
    """Tab bar + panel renderer using native HTML elements.

    Usage:
        tabs = Tabs([
            ("guests", "Guests", render_guests),
            ("admins", "Admins", render_admins),
        ])
        await tabs.build()
    """

    def __init__(
        self,
        tabs: list[tuple[str, str, Callable[[], Awaitable[None]]]],
        default: str | None = None,
    ):
        self.tabs = tabs
        self.active = default or tabs[0][0]

    def _select(self, key: str):
        self.active = key
        self.build.refresh()  # type: ignore

    @ui.refreshable
    async def build(self):
        with html.div().classes("rdm-tabs rdm-component"):
            for key, label, _ in self.tabs:
                cls = "rdm-tab rdm-active" if key == self.active else "rdm-tab"
                with html.button().classes(cls).on("click", lambda _, k=key: self._select(k)):
                    html.span(label)

        for key, _, render in self.tabs:
            if key == self.active:
                with html.div().classes("rdm-tab-panel"):
                    await render()
                break
