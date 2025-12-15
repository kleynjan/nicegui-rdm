"""
Refreshable components for reactive UI updates.

A *refreshable* is a UI component that maintains state and can be rebuilt on state changes.
It can be registered as an observer to one or more stores, so the UI can be updated when data changes.
Also, through on_state_change, it can notify other UI components of state changes.
"""

from typing import Callable
from nicegui import ui

from ..store.base import Store, StoreEvent

class StatefulRefreshable:
    """Container for UI components that are refreshed (=_rebuilt) whenever the state is updated (set_values)."""

    def __init__(self, state: dict, on_state_change: Callable[[dict], None] | None = None):
        self.state = state
        self.on_state_change = on_state_change

    def set_values(self, new_values: dict):
        # we may implement a filter method here as well? but for now filtering on store changes is enough...
        self.state.update(new_values)
        self.refresh()
        if self.on_state_change:
            self.on_state_change(self.state)

    def refresh(self):
        self.build.refresh()

    @ui.refreshable
    async def build(self):
        """Call this for the initial build."""
        await self._rebuild()

    async def _rebuild(self):
        """The actual @refreshable method, override in subclass."""
        ui.label(f"{self.__class__.__name__}._rebuild not implemented").classes("text-red")


class StoreRefreshable(StatefulRefreshable):
    """StatefulRefreshable with store registration, notification handling and filter option."""

    def __init__(self, state: dict, store: Store, on_state_change: Callable[[dict], None] | None = None):
        super().__init__(state, on_state_change)
        #
        # store create/update/delete -> callback -> self.refresh(**kwargs)
        self.store = store
        store.add_observer(self.handle_store_event)

    async def handle_store_event(self, event: StoreEvent):
        """Handle store notification (verb, item) and call self.refresh if it should be passed."""
        if self.filter(event):
            self.refresh()

    def filter(self, event: StoreEvent) -> bool:
        """Check store notification (verb, item) against self.state, return True if the instance should be refreshed."""

        # # example : basic multitenancy filter: only refresh events within same tenant
        # # not needed since we have per-tenant store instances
        # if event.item and "tenant" in event.item:
        #     if event.item["tenant"] != self.state["props"]["tenant"]:
        #         return False

        return True
