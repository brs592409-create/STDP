"""Lightweight and thread-safe EventBus for STDP inter-module communication."""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Type


class Event:
    """Base event class."""
    pass


class EventBus:
    """Thread-safe event bus for publishing and subscribing to typed events."""

    def __init__(self) -> None:
        self._subscribers: Dict[Type[Event], List[Callable[[Any], None]]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event_type: Type[Event], handler: Callable[[Any], None]) -> None:
        """Subscribe a callback to a specific event type."""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: Type[Event], handler: Callable[[Any], None]) -> None:
        """Unsubscribe a callback from a specific event type."""
        with self._lock:
            if event_type in self._subscribers and handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)

    def publish(self, event: Event) -> None:
        """Publish an event instance to all registered subscribers."""
        event_type = type(event)
        with self._lock:
            handlers = list(self._subscribers.get(event_type, []))

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # Avoid breaking the event dispatch loop if one handler fails
                pass


# Global singleton instance
event_bus = EventBus()
