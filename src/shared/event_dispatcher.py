from collections import defaultdict
from typing import Any, Callable, DefaultDict, List, Type


class EventDispatcher:
    """Simple synchronous event dispatcher."""

    def __init__(self) -> None:
        self._listeners: DefaultDict[Type, List[Callable[[Any], None]]] = defaultdict(
            list
        )

    def subscribe(self, event_type: Type, listener: Callable[[Any], None]) -> None:
        """Register a listener for a specific event type."""
        self._listeners[event_type].append(listener)

    def dispatch(self, event: Any) -> None:
        """Dispatch an event to all subscribed listeners."""
        for listener in self._listeners.get(type(event), []):
            listener(event)
