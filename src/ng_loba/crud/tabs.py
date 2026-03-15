"""
CrudTabs - div-based tab switcher, replacing Quasar QTabs.
Pure flexbox layout with crudy-tab-* CSS classes.
"""
from typing import Awaitable, Callable

from nicegui import ui


class CrudTabs:
    """Div-based tab bar + panel renderer.

    Usage:
        tabs = CrudTabs([
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
        with ui.row().classes("crudy-tab-bar"):
            for key, label, _ in self.tabs:
                cls = "crudy-tab-active" if key == self.active else "crudy-tab"
                ui.label(label).classes(cls).on("click", lambda _, k=key: self._select(k))

        for key, _, render in self.tabs:
            if key == self.active:
                with ui.column().classes("crudy-tab-panel"):
                    await render()
                break
