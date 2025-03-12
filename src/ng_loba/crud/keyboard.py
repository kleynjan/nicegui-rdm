"""
Keyboard event handling for CRUD components.
"""

from typing import Callable, List
from nicegui.events import KeyEventArguments

class ObservableKeyboard:
    """Observable keyboard events"""

    def __init__(self):
        self._observers: List[Callable[[KeyEventArguments], None]] = []

    def add_observer(self, observer: Callable[[KeyEventArguments], None]) -> None:
        """Add an observer to receive keyboard events"""
        self._observers.append(observer)

    def notify_observers(self, event: KeyEventArguments) -> None:
        """Notify observers of keyboard events"""
        for observer in self._observers:
            observer(event)
