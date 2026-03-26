"""
RDM Debug module - real-time event stream and store introspection.

Usage:
    from ng_rdm.debug import enable_debug_page
    enable_debug_page()  # Registers /rdm-debug route
"""

from .event_log import EventLog, EventLogEntry, event_log
from .page import enable_debug_page

__all__ = ["enable_debug_page", "EventLog", "EventLogEntry", "event_log"]
