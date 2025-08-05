import sys
from pathlib import Path

import pytest
from unittest.mock import Mock

sys.path.append(str(Path(__file__).resolve().parents[3] / "src"))

from shared.event_dispatcher import EventDispatcher


class TestEvent:
    def __init__(self, data: str):
        self.data = data


class TestEventDispatcher:
    def setup_method(self):
        self.dispatcher = EventDispatcher()

    def test_subscribes_and_dispatches_events(self):
        """Тест подписки и отправки событий."""
        listener = Mock()

        # Подписка
        self.dispatcher.subscribe(TestEvent, listener)

        # Отправка события
        event = TestEvent("test_data")
        self.dispatcher.dispatch(event)

        # Проверка
        listener.assert_called_once_with(event)

    def test_multiple_listeners_for_same_event(self):
        """Тест множественных слушателей для одного события."""
        listener1 = Mock()
        listener2 = Mock()

        self.dispatcher.subscribe(TestEvent, listener1)
        self.dispatcher.subscribe(TestEvent, listener2)

        event = TestEvent("test_data")
        self.dispatcher.dispatch(event)

        listener1.assert_called_once_with(event)
        listener2.assert_called_once_with(event)

    def test_no_listeners_for_event_type(self):
        """Тест отправки события без слушателей."""
        event = TestEvent("test_data")

        # Не должно вызывать ошибок
        self.dispatcher.dispatch(event)
