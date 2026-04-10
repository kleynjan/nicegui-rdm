"""
RDM Debug Page - real-time event stream visualization.

Provides a /rdm-debug route showing store activity, observers, and event stream.
"""

import time

from nicegui import ui

from ..store.base import store_registry
from ..store.multitenancy import mt_store_registry
from .event_log import EventLogEntry, event_log

VERB_COLORS = {
    "create": "#22c55e",  # green
    "update": "#3b82f6",  # blue
    "delete": "#ef4444",  # red
    "batch": "#6b7280",   # gray
}


def _time_ago(timestamp: float) -> str:
    """Format timestamp as 'Xs ago' or 'Xm ago'."""
    if timestamp == 0:
        return "never"
    diff = time.time() - timestamp
    if diff < 60:
        return f"{int(diff)}s ago"
    if diff < 3600:
        return f"{int(diff / 60)}m ago"
    return f"{int(diff / 3600)}h ago"


def _format_topics(topics: dict | None) -> str:
    """Format topics dict for display."""
    if topics is None:
        return "* (wildcard)"
    if not topics:
        return "{}"
    return ", ".join(f"{k}={v}" for k, v in topics.items())


def _render_debug_page() -> None:
    """Render the debug page content."""
    # State for live updates
    log_container = None
    stats_container = None

    def refresh_stats():
        """Refresh the store stats table."""
        if stats_container is None:
            return
        stats_container.clear()
        with stats_container:
            # Merge both registries: flat stores get tenant=""
            mt_stores = mt_store_registry.get_all_stores()  # [(tenant, name, store)]
            flat_stores = [("", name, store) for name, store in store_registry.get_all_stores()]
            all_stores: list[tuple[str, str, object]] = flat_stores + mt_stores
            show_tenant_col = bool(mt_stores)

            if not all_stores:
                ui.label("No stores registered yet").classes("text-gray-500 italic")
            else:
                # Get event stats for enrichment (event counts, last event time)
                event_stats = {(s.tenant, s.store_name): s for s in event_log.get_store_stats()}

                headers = ["Store", "Tenant", "Observers", "Events", "Last Event"] if show_tenant_col \
                    else ["Store", "Observers", "Events", "Last Event"]
                with ui.element("table").classes("w-full text-sm"):
                    with ui.element("thead").classes("bg-gray-100"):
                        with ui.element("tr"):
                            for header in headers:
                                ui.element("th").classes(
                                    "px-3 py-2 text-left font-medium").props(f'innerHTML="{header}"')
                    with ui.element("tbody"):
                        for tenant, name, store in all_stores:
                            stats = event_stats.get((tenant, name))
                            event_count = stats.event_count if stats else 0
                            last_event = stats.last_event_time if stats else 0
                            with ui.element("tr").classes("border-t"):
                                ui.element("td").classes("px-3 py-2 font-mono").props(f'innerHTML="{name}"')
                                if show_tenant_col:
                                    ui.element("td").classes("px-3 py-2").props(f'innerHTML="{tenant}"')
                                ui.element("td").classes(
                                    "px-3 py-2 text-center").props(f'innerHTML="{store.observer_count}"')  # type: ignore[union-attr]
                                ui.element("td").classes("px-3 py-2 text-center").props(f'innerHTML="{event_count}"')
                                ui.element("td").classes(
                                    "px-3 py-2 text-gray-500").props(f'innerHTML="{_time_ago(last_event)}"')

    def add_log_entry(entry: EventLogEntry):
        """Add a new entry to the log display."""
        if log_container is None:
            return
        with log_container:
            el = _render_log_entry(entry)
            el.move(log_container, 0)
        refresh_stats()

    def _render_log_entry(entry: EventLogEntry):
        """Render a single log entry."""
        color = VERB_COLORS.get(entry.event.verb, "#6b7280")
        with ui.element("div").classes("border-b py-2 px-3") as el:
            with ui.element("div").classes("flex items-center gap-2"):
                # Timestamp
                ui.label(entry.time_str).classes("font-mono text-xs text-gray-500 w-24")
                # Store + verb badge
                ui.element("span").classes("font-mono text-sm").props(f'innerHTML="{entry.store_name}"')
                ui.element("span").classes(
                    "px-2 py-0.5 rounded text-xs text-white").style(f"background-color: {color}").props(f'innerHTML="{entry.event.verb}"')
                # Arrow + observer
                ui.label("→").classes("text-gray-400")
                ui.element("span").classes("font-mono text-sm").props(f'innerHTML="{entry.observer_name}"')
                # Notified indicator
                if not entry.notified:
                    ui.element("span").classes("text-xs text-orange-500 ml-2").props('innerHTML="(filtered)"')
            # Topics line
            with ui.element("div").classes("ml-24 text-xs text-gray-500"):
                ui.label(f"topics: {_format_topics(entry.topics)}")
        return el

    # Page layout
    ui.label("RDM Event Stream").classes("text-2xl font-bold mb-4")

    # Controls
    with ui.row().classes("gap-4 mb-4 items-center"):
        enabled_switch = ui.switch("Enable logging", value=event_log.is_enabled)
        enabled_switch.on_value_change(lambda e: event_log.enable() if e.value else event_log.disable())

        ui.button("Clear", on_click=lambda: (event_log.clear(), refresh_log())).props("flat")
        ui.button("Refresh Stats", on_click=refresh_stats).props("flat")

    # Store overview section
    ui.label("Store Overview").classes("text-lg font-semibold mt-4 mb-2")
    stats_container = ui.element("div").classes("border rounded p-2 bg-white mb-4")
    refresh_stats()

    # Event log section
    ui.label("Event Log").classes("text-lg font-semibold mt-4 mb-2")
    ui.label("New events added at the top").classes("text-xs text-gray-500 mb-2")
    log_container = ui.element("div").classes("border rounded bg-white w-full")

    def refresh_log():
        """Refresh the entire log display."""
        log_container.clear()
        with log_container:
            entries = event_log.get_entries(limit=100)
            if entries:
                for entry in entries:
                    _render_log_entry(entry)

    refresh_log()

    # Register live update listener
    event_log.add_listener(add_log_entry)

    # Cleanup on disconnect
    async def cleanup():
        event_log.remove_listener(add_log_entry)

    ui.context.client.on_disconnect(cleanup)

    # Auto-refresh stats every 5 seconds
    ui.timer(5.0, refresh_stats)


def enable_debug_page(path: str = "/rdm-debug") -> None:
    """Register the RDM debug page route.

    Call this during app setup to enable the debug panel at /rdm-debug.
    This wires up event logging for all stores (existing and future).

    Args:
        path: URL path for the debug page (default: /rdm-debug)
    """
    @ui.page(path)
    def debug_page():
        _render_debug_page()

    # Enable event logging and wire up all stores (both flat and multitenant)
    event_log.enable()
    store_registry.set_event_log(event_log)
    mt_store_registry.set_event_log(event_log)
