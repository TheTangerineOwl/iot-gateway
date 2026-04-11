"""Общие фикстуры для всех модулей."""
import logging
import pytest
import pytest_asyncio
import psycopg
from unittest.mock import AsyncMock
from core.message_bus import MessageBus
from core.registry import DeviceRegistry
from models.device import DeviceStatus, DeviceType, Device, ProtocolType
from models.message import Message, MessageType


# PostgreSQL
PGSQL_CONNSTR = "postgresql://test:test@localhost:5432/testdb"
PGSQL_TIMEOUT = 2

# DeviceRegistry
REGISTRY_MAX_DEVICES = 5
REGISTRY_STALE_TIMEOUT = 120.0

# MessageBus
BUS_MAX_QUEUE = 100
BUS_DISPATCH_WAIT = 0.05

# Тестовые устройства
DEVICE_ID_DEFAULT = "dev-001"
DEVICE_ID_ONLINE = "dev-online"
DEVICE_NAME = "Thermometer"
DEVICE_DEF_PAYLOAD = {"temp": 42.0}


@pytest.fixture(autouse=True, scope='session')
def supress_loggers():
    """
    Подавляет указанные логгеры.

    В основном используется для того, чтобы не усеивать
    весь вывод pytest предупреждениями из шины о том,
    что не было найдено подписчика на сообщение.
    """
    bus_logger = logging.getLogger('core.message_bus')
    bus_logger.setLevel(logging.ERROR)
    bus_logger.propagate = False


def pytest_configure(config):
    """Настройка pytest."""
    config.addinivalue_line(
        'markers',
        'integration: требует запущенного PostgreSQL'
    )


pgsql_skip = False


def _postgres_available(flag: bool) -> bool:
    try:
        if flag:
            return False
        with psycopg.connect(
            PGSQL_CONNSTR,
            connect_timeout=PGSQL_TIMEOUT
        ):
            flag = False
            return True
    except Exception:
        flag = True
        return False


skip_no_postgres = pytest.mark.skipif(
    not _postgres_available(pgsql_skip),
    reason='PostgreSQL недоступен'
)


@pytest.fixture
def registry():
    """Реестр с маленьким лимитом устройств и долгим stale-таймаутом."""
    return DeviceRegistry(
        max_devices=REGISTRY_MAX_DEVICES,
        stale_timeout=REGISTRY_STALE_TIMEOUT
    )


@pytest.fixture
def device():
    """Устройство со всеми явными полями, чтобы тесты не зависели от uuid4."""
    return Device(
        device_id=DEVICE_ID_DEFAULT,
        name=DEVICE_NAME,
        device_type=DeviceType.SENSOR,
        device_status=DeviceStatus.ONLINE,
        protocol=ProtocolType.HTTP,
    )


@pytest_asyncio.fixture
async def running_bus():
    """Рабочая шина."""
    bus = MessageBus(max_queue=BUS_MAX_QUEUE)
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
def telemetry_message():
    """Тестовое сообщение телеметрии."""
    return Message(
        device_id=DEVICE_ID_DEFAULT,
        message_type=MessageType.TELEMETRY,
        payload=DEVICE_DEF_PAYLOAD,
        protocol=ProtocolType.HTTP,
    )


@pytest.fixture
def mock_storage():
    """Мок хранилища."""
    storage = AsyncMock()
    storage.save = AsyncMock()
    storage.setup = AsyncMock()
    storage.teardown = AsyncMock()
    return storage
