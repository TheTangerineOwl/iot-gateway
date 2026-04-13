"""Фикстуры для тестов адаптеров протоколов."""
import pytest
import pytest_asyncio
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from core.message_bus import MessageBus
from core.registry import DeviceRegistry
from protocols.adapters.http_adapter import HTTPAdapter


@pytest_asyncio.fixture
async def http_adapter(running_bus: MessageBus, registry: DeviceRegistry):
    """HTTP-адаптер, подключённый к шине."""
    a = HTTPAdapter()
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
