"""Тесты для HTTPAdapter."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
import asyncio
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from http import HTTPStatus
from protocols.adapters.http_adapter import HTTPAdapter
from core.message_bus import MessageBus
from core.registry import DeviceRegistry
from models.message import MessageType, Message


@pytest_asyncio.fixture
async def adapter(running_bus: MessageBus, registry: DeviceRegistry):
    """HTTP-адаптер, подключённый к шине, с поднятым тестовым сервером."""
    a = HTTPAdapter()
    a.set_gateway_context(running_bus, registry)
    yield a


@pytest.fixture
def url_telemetry(adapter: HTTPAdapter):
    """URL телеметрии."""
    return adapter._wh_telemetry


@pytest.fixture
def url_register(adapter: HTTPAdapter):
    """URL регистрации."""
    return adapter._url_register


@pytest.fixture
def url_health(adapter: HTTPAdapter):
    """URL проверки состояния."""
    return adapter._url_health


@pytest_asyncio.fixture
async def client(adapter: HTTPAdapter):
    """
    Фикстура клиента.

    Клиент aiohttp TestClient — не занимает реальный порт,
    общается с приложением напрямую.
    """
    app = web.Application()
    app.router.add_post(adapter._wh_telemetry, adapter._handle_ingest)
    app.router.add_post(adapter._url_register, adapter._handle_register)
    app.router.add_get(adapter._url_health, adapter._handle_health)

    adapter._running = True

    server = TestServer(app)
    cli = TestClient(server)
    await cli.start_server()
    yield cli
    await cli.close()


class TestProtocolName:
    """Тест на возврат имени протокола."""

    @pytest.mark.unit
    def test_returns_http(self, adapter: HTTPAdapter):
        """Возвращается корректное имя протокола."""
        assert adapter.protocol_name == 'HTTP'


class TestLifecycle:
    """Тестирование жизненного цикла адаптера."""

    @pytest.mark.unit
    async def test_start_sets_running(self, adapter: HTTPAdapter):
        """После запуска адаптера свойство running=True."""
        mock_runner = AsyncMock()
        mock_site = AsyncMock()

        with (
            patch(
                'aiohttp.web.AppRunner',
                return_value=mock_runner
            ),
            patch(
                'aiohttp.web.TCPSite',
                return_value=mock_site
            )
        ):
            await adapter.start()
            assert adapter._running is True
            assert adapter.is_running is True
            await adapter.stop()

    @pytest.mark.unit
    async def test_stop_clears_running(self, adapter: HTTPAdapter):
        """После остановки адаптера свойство running=False."""
        mock_runner = AsyncMock()
        mock_site = AsyncMock()

        with (
            patch(
                'aiohttp.web.AppRunner',
                return_value=mock_runner
            ),
            patch(
                'aiohttp.web.TCPSite',
                return_value=mock_site
            )
        ):
            await adapter.start()
            await adapter.stop()
            assert adapter._running is False
            assert adapter.is_running is False


class TestHandleIngest:
    """Тест обработки телеметрии."""

    @pytest.mark.unit
    async def test_valid_tm_returns_202(
        self, client: TestClient, url_telemetry
    ):
        """Запрос с корректным телом возвращает ACCEPTED."""
        resp = await client.post(
            url_telemetry,
            json={'device_id': 'dev-001', 'payload': {'temp': 23.5}},
        )
        assert resp.status == HTTPStatus.ACCEPTED

    @pytest.mark.unit
    async def test_body_status_and_message_id(
        self, client: TestClient, url_telemetry
    ):
        """В теле ответа поля status=accepted и message_id."""
        resp = await client.post(
            url_telemetry,
            json={'device_id': 'dev-001', 'payload': {'temp': 23.5}},
        )
        data = await resp.json()
        assert data['status'] == 'accepted'
        assert 'message_id' in data

    @pytest.mark.unit
    async def test_missing_device_id_returns_400(
        self, client: TestClient, url_telemetry
    ):
        """Если в сообщении нет device_id, вернет BAD_REQUEST."""
        resp = await client.post(
            url_telemetry,
            json={'payload': {'temp': 23.5}},
        )
        assert resp.status == HTTPStatus.BAD_REQUEST

    @pytest.mark.unit
    async def test_erron_missing_device_id(
        self, client: TestClient, url_telemetry
    ):
        """Если возникла ошибка, вернет ответ с информацией о ней."""
        resp = await client.post(
            url_telemetry,
            json={'payload': {'temp': 23.5}},
        )
        data = await resp.json()
        assert data.get('status', '') == 'error'
        assert data.get('error_code', 'no_code') == 'MISSING_DEVICE_ID'

    @pytest.mark.unit
    async def test_invalid_json_returns_400(
        self, client: TestClient, url_telemetry
    ):
        """Некорректный формат запроса вернет BAD_REQUEST."""
        resp = await client.post(
            url_telemetry,
            data='not-json',
            headers={'Content-Type': 'application/json'},
        )
        assert resp.status == HTTPStatus.BAD_REQUEST

    @pytest.mark.unit
    async def test_publish_to_bus(
        self, client: TestClient, running_bus: MessageBus, url_telemetry
    ):
        """Сообщение публикуется в шину сообщений корректно."""
        received = []

        async def _handler(msg):
            """Заглушка для обработчика."""
            received.append(msg)

        running_bus.subscribe('telemetry.dev-42', lambda m: _handler(m))

        await client.post(
            url_telemetry,
            json={'device_id': 'dev-42', 'payload': {'v': 1}},
        )
        await asyncio.sleep(0.05)

        assert len(received) == 1
        assert received[0].device_id == 'dev-42'
        assert received[0].message_type == MessageType.TELEMETRY

    @pytest.mark.unit
    async def test_topic_matches_device(
        self, client: TestClient, running_bus: MessageBus, url_telemetry
    ):
        """Топик сообщения соответствует запросу."""
        received = []

        async def _handler(m: Message) -> None:
            """Заглушка для обработчика."""
            received.append(m)

        running_bus.subscribe('telemetry.sensor-99', lambda m: _handler(m))

        await client.post(
            url_telemetry,
            json={'device_id': 'sensor-99', 'payload': {}},
        )
        await asyncio.sleep(0.05)

        assert received[0].message_topic == url_telemetry


class TestHandleRegister:
    """Тест обработки регистрации."""

    @pytest.mark.unit
    async def test_valid_register_returns_201(
        self, client: TestClient, url_register
    ):
        """Корректный запрос регистрации получит в ответ CREATED."""
        resp = await client.post(
            url_register,
            json={'device_id': 'dev-001', 'name': 'Sensor A'},
        )
        assert resp.status == HTTPStatus.CREATED

    @pytest.mark.unit
    async def test_valid_register_body_contains_status(
        self, client: TestClient, url_register
    ):
        """
        Тест ответа на корректный запрос регистрации.

        В ответе на корректный запрос регистрации будет status=registered.
        """
        resp = await client.post(
            url_register,
            json={'device_id': 'dev-001', 'name': 'Sensor A'},
        )
        data = await resp.json()
        assert data['status'] == 'registered'

    @pytest.mark.unit
    async def test_invalid_json_returns_400(
        self, client: TestClient, url_register
    ):
        """Некорректный формат запроса регистрации получит BAD_REQUEST."""
        resp = await client.post(
            url_register,
            data='bad',
            headers={'Content-Type': 'application/json'},
        )
        assert resp.status == HTTPStatus.BAD_REQUEST

    @pytest.mark.unit
    async def test_publishes_registration_to_bus(
        self, client: TestClient, running_bus: MessageBus, url_register
    ):
        """Сообщение о регистрации попадает на шину."""
        received = []

        async def handler(msg):
            received.append(msg)

        running_bus.subscribe('device.register.*', handler)

        await client.post(
            url_register,
            json={'device_id': 'dev-reg-1', 'name': 'Node'},
        )
        await asyncio.sleep(0.05)

        assert len(received) == 1
        assert received[0].message_type == MessageType.REGISTRATION
        assert received[0].device_id == 'dev-reg-1'

    @pytest.mark.unit
    async def test_message_topic_set_to_device_register(
        self, client: TestClient, running_bus: MessageBus, url_register
    ):
        """
        Тест топика сообщения регистрации на шине.

        Топик сообщения на шине будет формата device.register.{device_id}.
        """
        received = []

        async def _handler(m: Message) -> None:
            """Заглушка обработчика."""
            received.append(m)

        running_bus.subscribe('device.register.*', lambda m: _handler(m))

        await client.post(
            url_register,
            json={'device_id': 'dev-topic-test'},
        )
        await asyncio.sleep(0.05)

        assert received[0].message_topic == 'device.register.dev-topic-test'

    @pytest.mark.unit
    async def test_register_without_device_id(
        self, client: TestClient, url_register
    ):
        """Адаптер не проверяет наличие device_id при регистрации."""
        resp = await client.post(
            url_register,
            json={'name': 'Anonymous'},
        )
        # assert resp.status == HTTPStatus.CREATED
        assert resp.status == HTTPStatus.BAD_REQUEST


class TestHandleHealth:
    """Тест обработки проверки состояния."""

    @pytest.mark.unit
    async def test_health_returns_200(
        self, client: TestClient, url_health
    ):
        """Проверка состояния вернет OK."""
        resp = await client.get(
            url_health,
            json={},
        )
        assert resp.status == HTTPStatus.OK

    @pytest.mark.unit
    async def test_health_contains_protocol(
        self, client: TestClient, url_health
    ):
        """Проверка состояния содержит информацию о протоколе (HTTP)."""
        resp = await client.get(url_health, json={})
        data = await resp.json()
        assert data['protocol'] == 'HTTP'

    @pytest.mark.unit
    async def test_health_contains_running(
        self, client: TestClient, url_health
    ):
        """В проверке состояния есть информация о том, запущен ли адаптер."""
        resp = await client.get(url_health, json={})
        data = await resp.json()
        assert 'running' in data

    @pytest.mark.unit
    async def test_health_running_is_true_when_adapter_running(
        self, client: TestClient, url_health
    ):
        """Когда адаптер запущен, running=True."""
        resp = await client.get(url_health, json={})
        data = await resp.json()
        assert data['running'] is True


class TestHealthCheck:
    """Проверка состояния адаптера."""

    @pytest.mark.unit
    async def test_health_check_returns_dict(self, adapter: HTTPAdapter):
        """При проверке состояния адаптера возвращается словарь."""
        adapter._running = True
        result = await adapter._health_check()
        assert isinstance(result, dict)

    @pytest.mark.unit
    async def test_health_check_protocol_name(self, adapter: HTTPAdapter):
        """При проверке состояния адаптера возвращается имя протокола."""
        result = await adapter._health_check()
        assert result['protocol'] == 'HTTP'

    @pytest.mark.unit
    async def test_health_check_running_field(self, adapter: HTTPAdapter):
        """При проверке состояния адаптера возвращается running=True."""
        adapter._running = True
        result = await adapter._health_check()
        assert result['running'] is True
