"""Фикстуры для тестов адаптеров протоколов."""
import pytest
import pytest_asyncio
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from aiocoap import Message as CoAPMessage, POST as COAP_POST
from unittest.mock import AsyncMock, MagicMock
from typenv import Env
from config.config import load_env, YAMLConfigLoader
from core.message_bus import MessageBus
from core.registry import DeviceRegistry
from protocols.adapters.http_adapter import HTTPAdapter
from protocols.adapters.websocket_adapter import WebSocketAdapter
from protocols.adapters.mqtt_adapter import MQTTAdapter
from protocols.adapters.coap_adapter import (
    CoAPAdapter, _IngestResource, _RegisterResource, _HealthResource
)
from tests.conftest import (
    DEVICE_DEF_ID, MSG_DEF_PAYLOAD
)


load_env('env.example')
env = Env(upper=True)


@pytest_asyncio.fixture
async def http_adapter(
    config: YAMLConfigLoader,
    running_bus: MessageBus,
    registry: DeviceRegistry
):
    """HTTP-адаптер, подключённый к шине."""
    a = HTTPAdapter(config)
    a.set_gateway_context(running_bus, registry)
    yield a


@pytest_asyncio.fixture
async def http_client(http_adapter: HTTPAdapter):
    """
    Тестовый HTTP-клиент.

    Использует aiohttp TestClient — не занимает реальный порт,
    общается с приложением напрямую через TestServer.
    """
    app = web.Application()
    app.router.add_post(
        http_adapter._wh_telemetry,
        http_adapter._handle_ingest
    )
    app.router.add_post(
        http_adapter._url_register,
        http_adapter._handle_register
    )
    app.router.add_get(
        http_adapter._url_health,
        http_adapter._handle_health
    )

    http_adapter._running = True

    server = TestServer(app)
    cli = TestClient(server)
    await cli.start_server()
    yield cli
    await cli.close()


@pytest.fixture
def http_url_telemetry(http_adapter: HTTPAdapter) -> str:
    """URL эндпоинта телеметрии."""
    return http_adapter._wh_telemetry


@pytest.fixture
def http_url_register(http_adapter: HTTPAdapter) -> str:
    """URL эндпоинта регистрации."""
    return http_adapter._url_register


@pytest.fixture
def http_url_health(http_adapter: HTTPAdapter) -> str:
    """URL эндпоинта проверки состояния."""
    return http_adapter._url_health


WS_TELEMETRY_BODY = {
    'message_type': 'telemetry',
    'device_id': DEVICE_DEF_ID,
    'payload': MSG_DEF_PAYLOAD
}

WS_HEARTBEAT_BODY = {
    'message_type': 'heartbeat',
    'device_id': DEVICE_DEF_ID
}

WS_REGISTER_BODY = {
    'message_type': 'register',
    'device_id': DEVICE_DEF_ID,
    'payload': {'name': 'Sensor A'}
}

HTTP_REGISTER_BODY = {
    'device_id': DEVICE_DEF_ID,
    'name': 'Sensor A',
}


@pytest.fixture
async def ws_adapter(
    config: YAMLConfigLoader,
    running_bus: MessageBus,
    registry: DeviceRegistry
):
    """WebSocket-адаптер, подключенный к шине."""
    ws_adapter = WebSocketAdapter(config)
    ws_adapter.set_gateway_context(running_bus, registry)
    yield ws_adapter


@pytest.fixture
def ws_url_telemetry(ws_adapter: WebSocketAdapter) -> str:
    """URL WebSocket-эндпоинта телеметрии."""
    return ws_adapter._url_ws_telemetry


@pytest.fixture
def ws_url_register(ws_adapter: WebSocketAdapter) -> str:
    """URL эндпоинта регистрации."""
    return ws_adapter._url_register


@pytest.fixture
def ws_url_health(ws_adapter: WebSocketAdapter) -> str:
    """URL эндпоинта проверки состояния."""
    return ws_adapter._url_health


@pytest_asyncio.fixture
async def ws_client(ws_adapter: WebSocketAdapter):
    """
    Фикстура - aiohttp TestClient без реального порта.

    Маршруты регистрируются напрямую из адаптера,
    флаг _running выставляется вручную.
    """
    app = web.Application()
    app.router.add_get(
        ws_adapter._url_ws_telemetry,
        ws_adapter._handle_ws_ingest
    )
    app.router.add_post(ws_adapter._url_register, ws_adapter._handle_register)
    app.router.add_get(ws_adapter._url_register, ws_adapter._handle_ws_ingest)
    app.router.add_get(ws_adapter._url_health, ws_adapter._handle_health)
    ws_adapter._running = True

    server = TestServer(app)
    cli = TestClient(server)
    await cli.start_server()
    yield cli
    await cli.close()


@pytest_asyncio.fixture
async def coap_adapter(
    config: YAMLConfigLoader,
    running_bus: MessageBus,
    registry: DeviceRegistry
):
    """CoAP-адаптер, подключённый к реальной шине и реестру."""
    a = CoAPAdapter(config)
    a.set_gateway_context(running_bus, registry)
    yield a


def _make_adapter(
    config: YAMLConfigLoader,
    bus: MagicMock | None = None,
    registry: MagicMock | None = None,
) -> CoAPAdapter:
    """Создать CoAPAdapter с изолированными mock-зависимостями."""
    adapter = CoAPAdapter(config)
    if bus is None:
        mock_bus = MagicMock()
        mock_bus._config = config
        mock_bus.publish = AsyncMock()
        mock_bus.subscribe = MagicMock(return_value=MagicMock())
        mock_bus.unsubscribe = MagicMock()
        bus = mock_bus
    adapter.set_gateway_context(bus, registry or MagicMock())
    return adapter


def coap_request(payload: bytes = b"") -> CoAPMessage:
    """Сформировать минимальный CoAP-запрос с заданным payload."""
    return CoAPMessage(code=COAP_POST, payload=payload)


@pytest.fixture
def mock_adapter(config: YAMLConfigLoader) -> CoAPAdapter:
    """CoAP-адаптер с mock-шиной (для тестов без реальной шины)."""
    return _make_adapter(config)


@pytest.fixture
def coap_ingest(mock_adapter: CoAPAdapter) -> _IngestResource:
    """_IngestResource, привязанный к mock-адаптеру."""
    return _IngestResource(mock_adapter)


@pytest.fixture
def coap_register(mock_adapter: CoAPAdapter) -> _RegisterResource:
    """_RegisterResource, привязанный к mock-адаптеру."""
    return _RegisterResource(mock_adapter)


@pytest.fixture
def coap_health(mock_adapter: CoAPAdapter) -> _HealthResource:
    """_HealthResource, привязанный к mock-адаптеру."""
    return _HealthResource(mock_adapter)


@pytest.fixture
def mqtt_adapter(
    config: YAMLConfigLoader,
    running_bus: MessageBus,
    registry: DeviceRegistry
):
    """MQTT-адаптер для тестов."""
    adapter = MQTTAdapter(config)
    adapter.set_gateway_context(running_bus, registry)
    yield adapter
