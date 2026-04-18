"""Общие фикстуры для всех модулей."""
from contextlib import contextmanager
import asyncio
import logging
import pytest
import pytest_asyncio
import psycopg
from unittest.mock import AsyncMock
from config.config import YAMLConfigLoader
from core.message_bus import MessageBus
from core.registry import DeviceRegistry
from core.pipeline.pipeline import Pipeline
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
DEVICE_DEF_ID = "dev-001"
DEVICE_NAME = "Thermometer"
DEVICE_DEF_STATUS = DeviceStatus.ONLINE
DEVICE_DEF_PROTOCOL = ProtocolType.HTTP
DEVICE_DEF_TYPE = DeviceType.SENSOR

# Тестовое сообщение
MSG_DEF_ID = 'mes-001'
MSG_DEF_TOPIC = 'test.topic'
MSG_DEF_PROTOCOL = ProtocolType.HTTP
MSG_DEF_TYPE = MessageType.TELEMETRY
MSG_DEF_PAYLOAD = {"temp": 42.0}
MSG_DEF_META = {'meta': 'test'}
MSG_DEF_SCHEMA = '1.0'

# Топики
TOPIC_TELEMETRY_WC = 'telemetry.*'
TOPIC_TELEMETRY = 'telemetry.%s'
TOPIC_REGISTER_WC = 'device.register.*'
TOPIC_REGISTER = 'device.register.%s'


@contextmanager
def not_raises(exception: type[Exception]):
    """Проваливает тест в случае указанного исключения."""
    try:
        yield
    except exception as exc:
        raise pytest.fail(
            'DID RAISE {0}: {1}'.format(exception, exc)
        )


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
    asyncio_logger = logging.getLogger('asyncio')
    asyncio_logger.setLevel(logging.WARNING)


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


async def drain(bus: MessageBus) -> None:
    """Ждет, пока очередь опустеет."""
    deadline = asyncio.get_event_loop().time() + BUS_DISPATCH_WAIT
    while bus._queue.qsize() > 0:
        if asyncio.get_event_loop().time() > deadline:
            raise TimeoutError('Bus queue did not drain')
        await asyncio.sleep(0)


@pytest.fixture(scope='session')
def config():
    """Возвращает пустой конфиг."""
    loader = YAMLConfigLoader()
    loader.config = {'gateway': {'message_bus': {'max_queue': BUS_MAX_QUEUE}}}
    yield loader


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
    device = Device(
        device_id=DEVICE_DEF_ID,
        name=DEVICE_NAME,
        device_type=DEVICE_DEF_TYPE,
        device_status=DEVICE_DEF_STATUS,
        protocol=DEVICE_DEF_PROTOCOL,
    )
    device.last_response = device.created_at
    return device


@pytest_asyncio.fixture
async def running_bus(config):
    """Рабочая шина."""
    bus = MessageBus(config)
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
def telemetry_message():
    """Тестовое сообщение телеметрии."""
    return Message(
        message_id=MSG_DEF_ID,
        device_id=DEVICE_DEF_ID,
        message_type=MSG_DEF_TYPE,
        message_topic=MSG_DEF_TOPIC,
        payload=MSG_DEF_PAYLOAD,
        protocol=MSG_DEF_PROTOCOL,
        schema_version=MSG_DEF_SCHEMA,
        metadata=MSG_DEF_META
    )


@pytest.fixture
def mock_storage():
    """Мок хранилища."""
    storage = AsyncMock()
    storage.save = AsyncMock()
    storage.setup = AsyncMock()
    storage.teardown = AsyncMock()
    storage.get_by_device = AsyncMock()
    return storage


@pytest.fixture
def pipeline():
    """Тестовый конвейер."""
    return Pipeline()
