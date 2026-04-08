"""Общие фикстуры для всех модулей."""
import pytest
import psycopg
from unittest.mock import AsyncMock
from core.message_bus import MessageBus
from core.registry import DeviceRegistry
from models.device import DeviceStatus, DeviceType, Device, ProtocolType
from models.message import Message, MessageType


INTEGRATION_PGSQL_CONNSTR = 'postgresql://test:test@localhost:5433/testdb'


def pytest_configure(config):
    """Настройка pytest."""
    config.addinivalue_line(
        'markers',
        'integration: требует запущенного PostgreSQL'
    )


def _postgres_available() -> bool:
    try:
        with psycopg.connect(
            INTEGRATION_PGSQL_CONNSTR,
            connect_timeout=2
        ):
            return True
    except Exception:
        return False


skip_no_postgres = pytest.mark.skipif(
    not _postgres_available(),
    reason='PostgreSQL недоступен'
)


@pytest.fixture
def registry():
    """Реестр с маленьким лимитом устройств и долгим stale-таймаутом."""
    return DeviceRegistry(max_devices=5, stale_timeout=120.0)


@pytest.fixture
def device():
    """Устройство со всеми явными полями, чтобы тесты не зависели от uuid4."""
    return Device(
        device_id="dev-001",
        name="Thermometer",
        device_type=DeviceType.SENSOR,
        device_status=DeviceStatus.OFFLINE,
        protocol=ProtocolType.HTTP,
    )


@pytest.fixture
def message_bus():
    """Тестовая шина сообщений."""
    return MessageBus(max_queue=100)


@pytest.fixture
def telemetry_message():
    """Тестовое сообщение телеметрии."""
    return Message(
        device_id="dev-001",
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
