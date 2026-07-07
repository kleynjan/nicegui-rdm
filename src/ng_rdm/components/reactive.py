"""
ReactiveCounts — a throttled, binding-friendly count view over an RdmDataSource.

Counts bypass ``@ui.refreshable`` entirely: ng_rdm decides *when* to recompute (a
throttled store observer) and writes the numbers into a plain dict; NiceGUI's
``bind_text_from`` puts them on screen without re-rendering any table. This is the
"count-view" archetype for progress/summary headers over large or fast-changing data.
"""

from __future__ import annotations

from typing import Any

from nicegui import ui

from .protocol import RdmDataSource


class ReactiveCounts:
    """A small, reactive count-view for progress/summary headers.

    Registers a (throttled) observer on the data source and recomputes counts via
    ``read_counts()`` into ``self.values`` — a plain dict, mutated in place so NiceGUI
    bindings keep tracking it. No DOM, no ``@ui.refreshable``.

    Ungrouped counts are stored under ``key`` (default ``"total"``); grouped counts use
    the group values as keys. For grouped views, pre-seed expected groups via ``keys``
    so bindings always resolve (a group with zero rows is absent from the DB result).

    Usage::

        counts = ReactiveCounts(store, filter_by={"batch_id": 7},
                                group_by="status", keys=["delivered", "pending"])
        await counts.start()
        ui.label().bind_text_from(counts.values, "delivered", backward=lambda v: v or 0)
    """

    def __init__(
        self,
        data_source: RdmDataSource,
        filter_by: dict[str, Any] | None = None,
        q: Any | None = None,
        group_by: str | None = None,
        key: str = "total",
        keys: list[Any] | None = None,
    ) -> None:
        self.data_source = data_source
        self.filter_by = filter_by
        self.q = q
        self.group_by = group_by
        self.key = key
        # Stable dict object bindings can track; pre-seed keys to 0 so labels resolve.
        self.values: dict[Any, int] = {}
        if group_by is None:
            self.values[key] = 0
        else:
            for k in keys or []:
                self.values[k] = 0
        self._client: Any = None
        self._observing = False

    async def start(self) -> "ReactiveCounts":
        """Register the throttled observer, do an initial recompute, wire cleanup."""
        if self._observing:
            return self
        self._client = ui.context.client
        self.data_source.add_observer(self._recompute)
        self._observing = True
        self._client.on_disconnect(self.stop)
        await self._recompute()
        return self

    def stop(self) -> None:
        """Unregister the observer (called automatically on client disconnect)."""
        if self._observing:
            self.data_source.remove_observer(self._recompute)
            self._observing = False

    async def _recompute(self, event: Any = None) -> None:
        """Recompute counts and update self.values in place (mutate, never reassign)."""
        result = await self.data_source.read_counts(
            filter_by=self.filter_by, q=self.q, group_by=self.group_by
        )
        if self.group_by is None:
            self.values[self.key] = result  # type: ignore[assignment]
        else:
            assert isinstance(result, dict)
            # zero known groups first so a group that dropped to zero rows reads 0
            for k in self.values:
                self.values[k] = 0
            self.values.update(result)
