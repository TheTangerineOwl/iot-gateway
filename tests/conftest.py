"""Общие фикстуры для всех модулей."""
import pytest
from unittest.mock import AsyncMock
from core.message_bus import MessageBus
from models.message import Message, MessageType


@pytest.fixture
def message_bus():
    """Тестовая шина сообщений."""
    return MessageBus(max_queue=100)


@pytest.fixture
def telemetry_message():
    """Тестовое сообщение телеметрии."""
    return Message(
        device_id="dev-1",
        message_type=MessageType.TELEMETRY,
        payload={"temp": 42.0},
        protocol="http",
    )


@pytest.fixture
def mock_storage():
    """Мок хранилища."""
    storage = AsyncMock()
    storage.save = AsyncMock()
    storage.setup = AsyncMock()
    storage.teardown = AsyncMock()
    return storage
