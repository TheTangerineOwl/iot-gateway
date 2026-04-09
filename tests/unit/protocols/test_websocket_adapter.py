"""Тесты для WebSocketAdapter."""
import asyncio
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from aiohttp.test_utils import TestClient, TestServer
from aiohttp import web
from http import HTTPStatus
from protocols.websocket_adapter import WebSocketAdapter
from core.message_bus import MessageBus
from core.registry import DeviceRegistry
from models.message import MessageType, Message


@pytest_asyncio.fixture
async def adapter(running_bus: MessageBus, registry: DeviceRegistry):
    """WebSocket-адаптер, подключённый к шине."""
    a = WebSocketAdapter()
    a.set_gateway_context(running_bus, registry)
    yield a


@pytest.fixture
def url_telemetry(adapter: WebSocketAdapter):
    """URL телеметрии."""
    return adapter._url_ws_telemetry


@pytest.fixture
def url_register(adapter: WebSocketAdapter):
    """URL регистрации."""
    return adapter._url_register


@pytest.fixture
def url_health(adapter: WebSocketAdapter):
    """URL проверки состояния."""
    return adapter._url_health


@pytest_asyncio.fixture
async def client(adapter: WebSocketAdapter):
    """
    Клиент aiohttp TestClient — без реального порта.

    Маршруты регистрируются напрямую из адаптера.
    """
    app = web.Application()
    app.router.add_get(adapter._url_ws_telemetry, adapter._handle_ws_ingest)
    app.router.add_post(adapter._url_register, adapter._handle_register)
    app.router.add_get(adapter._url_register, adapter._handle_ws_ingest)
    app.router.add_get(adapter._url_health, adapter._handle_health)

    adapter._running = True

    server = TestServer(app)
    cli = TestClient(server)
    await cli.start_server()
    yield cli
    await cli.close()


async def _ws_exchange(
        client: TestClient, url: str, messages: list[dict]
) -> list[dict]:
    """
    Вспомогательная функция для обмена сообщениями.

    Открыть WS-соединение, последовательно отправить сообщения,
    собрать ответы и закрыть соединение.
    """
    responses = []
    async with client.ws_connect(url) as ws:
        for msg in messages:
            await ws.send_str(json.dumps(msg))
            resp = await asyncio.wait_for(ws.receive_json(), timeout=2.0)
            responses.append(resp)
    return responses


class TestProtocolName:
    """Тест вывода имени протокола."""

    @pytest.mark.unit
    def test_returns_websocket(self, adapter: WebSocketAdapter):
        """Вывод имени протокола возвращает WebSocket."""
        assert adapter.protocol_name == "WebSocket"


class TestLifecycle:
    """Тест жизненного цикла."""

    @pytest.mark.unit
    async def test_start_sets_running(self, adapter: WebSocketAdapter):
        """После запуска адаптера свойство running=True."""
        with (
            patch('protocols.websocket_adapter.web.AppRunner') as mock_runner,
            patch('protocols.websocket_adapter.web.TCPSite') as mock_site
        ):
            mock_runner.return_value.setup = AsyncMock()
            mock_site.return_value.start = AsyncMock()
            mock_runner.return_value.cleanup = AsyncMock()

            await adapter.start()
            assert adapter._running is True
            await adapter.stop()

    @pytest.mark.unit
    async def test_stop_clears_running(self, adapter: WebSocketAdapter):
        """После остановки адаптера свойство running=False."""
        with (
            patch('protocols.websocket_adapter.web.AppRunner') as mock_runner,
            patch('protocols.websocket_adapter.web.TCPSite') as mock_site
        ):
            mock_runner.return_value.setup = AsyncMock()
            mock_site.return_value.start = AsyncMock()
            mock_runner.return_value.cleanup = AsyncMock()

            await adapter.start()
            await adapter.stop()
            assert adapter._running is False

    @pytest.mark.unit
    async def test_stop_closes_active_connections(
        self, adapter: WebSocketAdapter
    ):
        """Остановка закрывает все активные WS-соединения и очищает словарь."""
        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()
        adapter._connections["dev-x"] = mock_ws

        with (
            patch('protocols.websocket_adapter.web.AppRunner') as mock_runner,
            patch('protocols.websocket_adapter.web.TCPSite') as mock_site
        ):
            mock_runner.return_value.setup = AsyncMock()
            mock_site.return_value.start = AsyncMock()
            mock_runner.return_value.cleanup = AsyncMock()

            await adapter.start()
            await adapter.stop()

        mock_ws.close.assert_awaited_once()
        assert adapter._connections == {}


class TestWsTelemetry:
    """Проверка обработки телеметрии."""

    @pytest.mark.unit
    async def test_telemetry_returns_accepted(
        self, client: TestClient, url_telemetry
    ):
        """Ответ на корректное сообщение содержит status=accepted."""
        responses = await _ws_exchange(
            client,
            url_telemetry,
            [{
                "type": "telemetry",
                "device_id": "dev-1",
                "payload": {"temp": 22.0}
            }],
        )
        assert responses[0]["status"] == "accepted"

    @pytest.mark.unit
    async def test_telemetry_response_contains_message_id(
        self, client: TestClient, url_telemetry
    ):
        """Ответ на телеметрию содержит message_id."""
        responses = await _ws_exchange(
            client,
            url_telemetry,
            [{"type": "telemetry", "device_id": "dev-1", "payload": {}}],
        )
        assert "message_id" in responses[0]

    @pytest.mark.unit
    async def test_telemetry_publishes_to_bus(
        self, client: TestClient, url_telemetry, running_bus: MessageBus
    ):
        """Телеметрия попадает на шину."""
        received = []

        async def handler(msg):
            """Заглушка обработчика."""
            received.append(msg)

        running_bus.subscribe("telemetry.ws-dev-1", handler)

        await _ws_exchange(
            client,
            url_telemetry,
            [{
                "type": "telemetry",
                "device_id": "ws-dev-1",
                "payload": {"v": 7}
            }],
        )
        await asyncio.sleep(0.05)

        assert len(received) == 1
        assert received[0].message_type == MessageType.TELEMETRY
        assert received[0].device_id == "ws-dev-1"

    @pytest.mark.unit
    async def test_telemetry_message_topic(
        self, client: TestClient, url_telemetry, running_bus: MessageBus
    ):
        """Топик сообщения по шаблону telemetry.{device_id}."""
        received = []

        async def _handler(msg: Message):
            """Заглушка обработчика."""
            received.append(msg)

        running_bus.subscribe("telemetry.*", lambda m: _handler(m))

        await _ws_exchange(
            client,
            url_telemetry,
            [{"type": "telemetry", "device_id": "topic-dev", "payload": {}}],
        )
        await asyncio.sleep(0.05)

        assert received[0].message_topic == "telemetry.topic-dev"

    @pytest.mark.unit
    async def test_telemetry_default_type_when_omitted(
        self, client: TestClient, url_telemetry, running_bus: MessageBus
    ):
        """Если поле type не передано, по умолчанию считается telemetry."""
        received = []

        async def _handler(msg: Message):
            """Заглушка обработчика."""
            received.append(msg)

        running_bus.subscribe("telemetry.*", lambda m: _handler(m))

        await _ws_exchange(
            client,
            url_telemetry,
            [{"device_id": "dev-no-type", "payload": {"x": 1}}],
        )
        await asyncio.sleep(0.05)

        assert len(received) == 1
        assert received[0].message_type == MessageType.TELEMETRY


class TestWsHeartbeat:
    """Тест проверки состояния (WS)."""

    @pytest.mark.unit
    async def test_heartbeat_returns_ok(
        self, client: TestClient, url_telemetry
    ):
        """Проверка состояния получает OK."""
        responses = await _ws_exchange(
            client,
            url_telemetry,
            [{"type": "heartbeat", "device_id": "dev-hb"}],
        )
        assert responses[0]["status"] == "ok"

    @pytest.mark.unit
    async def test_heartbeat_publishes_to_bus(
        self, client: TestClient, url_telemetry, running_bus: MessageBus
    ):
        """Проверка состояния попадает на шину."""
        received = []

        async def _handler(msg):
            """Заглушка обработчика."""
            received.append(msg)

        running_bus.subscribe("device.heartbeat.*", lambda m: _handler(m))

        await _ws_exchange(
            client,
            url_telemetry,
            [{"type": "heartbeat", "device_id": "dev-hb-2"}],
        )
        await asyncio.sleep(0.05)

        assert len(received) == 1
        assert received[0].message_type == MessageType.HEARTBEAT
        assert received[0].device_id == "dev-hb-2"

    @pytest.mark.unit
    async def test_heartbeat_message_topic(
        self, client: TestClient, url_telemetry, running_bus: MessageBus
    ):
        """Проверка состояния имеет топик device.heartbeat.{device_id}."""
        received = []

        async def _handler(msg: Message):
            """Заглушка обработчика."""
            received.append(msg)

        running_bus.subscribe("device.heartbeat.*", lambda m: _handler(m))

        await _ws_exchange(
            client,
            url_telemetry,
            [{"type": "heartbeat", "device_id": "hb-topic"}],
        )
        await asyncio.sleep(0.05)

        assert received[0].message_topic == "device.heartbeat.hb-topic"


class TestWsRegister:
    """Тесты регистрации."""

    @pytest.mark.unit
    async def test_register_returns_registered(
        self, client: TestClient, url_register
    ):
        """Регистрация возвращает status=registered."""
        responses = await _ws_exchange(
            client,
            url_register,
            [{
                "type": "register",
                "device_id": "dev-reg",
                "payload": {"name": "X"}
            }],
        )
        assert responses[0]["status"] == "registered"

    @pytest.mark.unit
    async def test_register_publishes_to_bus(
        self, client: TestClient, url_register, running_bus: MessageBus
    ):
        """Сообщение о регистрации попадает на шину."""
        received = []

        async def _handler(msg):
            """Заглушка обработчика."""
            received.append(msg)

        running_bus.subscribe("device.register.*", lambda m: _handler(m))

        await _ws_exchange(
            client,
            url_register,
            [{"type": "register", "device_id": "dev-reg-2", "payload": {}}],
        )
        await asyncio.sleep(0.05)

        assert len(received) == 1
        assert received[0].message_type == MessageType.REGISTRATION
        assert received[0].device_id == "dev-reg-2"

    @pytest.mark.unit
    async def test_register_message_topic(
        self, client: TestClient, url_register, running_bus: MessageBus
    ):
        """Топик регистрации по шаблону device.register.{device_id}."""
        received = []

        async def _handler(msg):
            """Заглушка обработчика."""
            received.append(msg)

        running_bus.subscribe("device.register.*", lambda m: _handler(m))

        await _ws_exchange(
            client,
            url_register,
            [{
                "type": "register", "device_id": "dev-topic-reg", "payload": {}
            }],
        )
        await asyncio.sleep(0.05)

        assert received[0].message_topic == "device.register.dev-topic-reg"


class TestWsErrors:
    """Тесты на различные ошибки."""

    @pytest.mark.unit
    async def test_invalid_json_returns_error(
        self, client: TestClient, url_telemetry
    ):
        """Некорректный формат вызовет ошибку."""
        async with client.ws_connect(url_telemetry) as ws:
            await ws.send_str("this is not json{{{")
            resp = await asyncio.wait_for(ws.receive_json(), timeout=2.0)
        assert "error" in resp

    @pytest.mark.unit
    async def test_missing_device_id_returns_error(
        self, client: TestClient, url_telemetry
    ):
        """Пропущенный device_id вызовет ошибку."""
        async with client.ws_connect(url_telemetry) as ws:
            await ws.send_str(json.dumps({"type": "telemetry", "payload": {}}))
            resp = await asyncio.wait_for(ws.receive_json(), timeout=2.0)
        assert "error" in resp

    @pytest.mark.unit
    async def test_unknown_message_type_returns_error(
        self, client: TestClient, url_telemetry
    ):
        """Неизвестный тип сообщения вызовет ошибку."""
        responses = await _ws_exchange(
            client,
            url_telemetry,
            [{"type": "unknown_type", "device_id": "dev-1"}],
        )
        assert "error" in responses[0]

    @pytest.mark.unit
    async def test_invalid_json_error_message_text(
        self, client: TestClient, url_telemetry
    ):
        """Сообщение об ошибке формата содержит информацию."""
        async with client.ws_connect(url_telemetry) as ws:
            await ws.send_str("<<<bad>>>")
            resp = await asyncio.wait_for(ws.receive_json(), timeout=2.0)
        assert resp["error"] == "Invalid JSON"

    @pytest.mark.unit
    async def test_missing_device_id_error_message_text(
        self, client: TestClient, url_telemetry
    ):
        """Сообщение о пропущенном id содержит информацию."""
        async with client.ws_connect(url_telemetry) as ws:
            await ws.send_str(json.dumps({"type": "telemetry"}))
            resp = await asyncio.wait_for(ws.receive_json(), timeout=2.0)
        assert resp["error"] == "device_id required"


class TestWsConnections:
    """Тесты подключений."""

    @pytest.mark.unit
    async def test_connection_registered_after_first_message(
        self, client: TestClient, adapter: WebSocketAdapter
    ):
        """После первого сообщения device_id в _connections."""
        async with client.ws_connect(adapter._url_ws_telemetry) as ws:
            await ws.send_str(
                json.dumps({
                    "type": "telemetry", "device_id": "conn-dev", "payload": {}
                })
            )
            await asyncio.wait_for(ws.receive_json(), timeout=2.0)
            assert "conn-dev" in adapter._connections

    @pytest.mark.unit
    async def test_connection_removed_after_close(
        self, client: TestClient, adapter: WebSocketAdapter
    ):
        """После закрытия device_id должен исчезнуть из _connections."""
        async with client.ws_connect(adapter._url_ws_telemetry) as ws:
            await ws.send_str(
                json.dumps({
                    "type": "telemetry",
                    "device_id": "close-dev",
                    "payload": {}
                })
            )
            await asyncio.wait_for(ws.receive_json(), timeout=2.0)

        await asyncio.sleep(0.05)
        assert "close-dev" not in adapter._connections

    @pytest.mark.unit
    async def test_multiple_messages_keep_same_connection(
        self, client: TestClient, adapter: WebSocketAdapter
    ):
        """Несколько сообщений от одного device_id не дублируют запись."""
        async with client.ws_connect(adapter._url_ws_telemetry) as ws:
            for i in range(3):
                await ws.send_str(
                    json.dumps({"type": "heartbeat", "device_id": "multi-dev"})
                )
                await asyncio.wait_for(ws.receive_json(), timeout=2.0)

            count = sum(1 for k in adapter._connections if k == "multi-dev")
            assert count == 1


class TestHttpRegister:
    """Тесты регистрации."""

    @pytest.mark.unit
    async def test_valid_register_returns_201(
        self, client: TestClient, url_register
    ):
        """На корректный запрос ответ CREATED."""
        resp = await client.post(
            url_register,
            json={"device_id": "http-reg-dev", "name": "Sensor B"},
        )
        assert resp.status == HTTPStatus.CREATED

    @pytest.mark.unit
    async def test_valid_register_body_contains_status(
        self, client: TestClient, url_register
    ):
        """Ответ на корректный запрос содержит status=registered."""
        resp = await client.post(
            url_register,
            json={"device_id": "http-reg-dev"},
        )
        data = await resp.json()
        assert data["status"] == "registered"

    @pytest.mark.unit
    async def test_invalid_json_returns_400(
        self, client: TestClient, url_register
    ):
        """Некорректный запрос получит BAD_REQUEST."""
        resp = await client.post(
            url_register,
            data="bad-json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status == HTTPStatus.BAD_REQUEST

    @pytest.mark.unit
    async def test_invalid_json_body_contains_error(
        self, client: TestClient, url_register
    ):
        """Некорректный запрос содержит информацию об ошибке."""
        resp = await client.post(
            url_register,
            data="bad-json",
            headers={"Content-Type": "application/json"},
        )
        data = await resp.json()
        assert "error" in data

    @pytest.mark.unit
    async def test_publishes_registration_to_bus(
        self, client: TestClient, url_register, running_bus: MessageBus
    ):
        """Сообщение о регистрации попадает на шину."""
        received = []

        async def _handler(msg):
            received.append(msg)

        running_bus.subscribe("device.register.*", lambda m: _handler(m))

        await client.post(
            url_register,
            json={"device_id": "http-bus-dev"},
        )
        await asyncio.sleep(0.05)

        assert len(received) == 1
        assert received[0].message_type == MessageType.REGISTRATION
        assert received[0].device_id == "http-bus-dev"

    @pytest.mark.unit
    async def test_message_topic_set_correctly(
        self, client: TestClient, url_register, running_bus: MessageBus
    ):
        """Топик сообщения задается корректно."""
        received = []

        async def _handler(msg):
            received.append(msg)

        running_bus.subscribe("device.register.*", lambda m: _handler(m))

        await client.post(
            url_register,
            json={"device_id": "topic-check-dev"},
        )
        await asyncio.sleep(0.05)

        assert received[0].message_topic == "device.register.topic-check-dev"


class TestHttpHealth:
    """Тесты проверки состояния."""

    @pytest.mark.unit
    async def test_health_returns_200(
        self, client: TestClient, url_health
    ):
        """Проверка состояния получает OK."""
        resp = await client.get(url_health)
        assert resp.status == HTTPStatus.OK

    @pytest.mark.unit
    async def test_health_contains_protocol(
        self, client: TestClient, url_health
    ):
        """Проверка состояния возвращает протокол."""
        resp = await client.get(url_health)
        data = await resp.json()
        assert data["protocol"] == "WebSocket"

    @pytest.mark.unit
    async def test_health_contains_running(
        self, client: TestClient, url_health
    ):
        """Проверка состояния возвращает статус адаптера."""
        resp = await client.get(url_health)
        data = await resp.json()
        assert "running" in data

    @pytest.mark.unit
    async def test_health_contains_connections_count(
        self, client: TestClient, url_health
    ):
        """Проверка состояния возвращает количество подключений."""
        resp = await client.get(url_health)
        data = await resp.json()
        assert "connections" in data

    @pytest.mark.unit
    async def test_health_connections_count_is_zero_initially(
        self, client: TestClient, url_health
    ):
        """Проверка состояния без подключений вернет количеством 0."""
        resp = await client.get(url_health)
        data = await resp.json()
        assert data["connections"] == 0

    @pytest.mark.unit
    async def test_health_connections_count_increases(
        self, client: TestClient, adapter: WebSocketAdapter
    ):
        """После установки WS-соединения счётчик в /health должен вырасти."""
        async with client.ws_connect(adapter._url_ws_telemetry) as ws:
            await ws.send_str(
                json.dumps({
                    "type": "heartbeat",
                    "device_id": "health-count-dev"
                })
            )
            await asyncio.wait_for(ws.receive_json(), timeout=2.0)

            resp = await client.get(adapter._url_health)
            data = await resp.json()
            assert data["connections"] >= 1

    @pytest.mark.unit
    async def test_health_running_is_true_when_adapter_running(
        self, client: TestClient, url_health
    ):
        """Когда адаптер запущен, running=True в ответе."""
        resp = await client.get(url_health)
        data = await resp.json()
        assert data["running"] is True


class TestHealthCheck:
    """Тест проверки состояния (без HTTP)."""

    @pytest.mark.unit
    async def test_health_check_returns_dict(self, adapter: WebSocketAdapter):
        """Ответ на проверку состония - словарь."""
        result = await adapter._health_check()
        assert isinstance(result, dict)

    @pytest.mark.unit
    async def test_health_check_protocol_name(self, adapter: WebSocketAdapter):
        """Ответ на проверку состояния содержит протокол."""
        result = await adapter._health_check()
        assert result["protocol"] == "WebSocket"

    @pytest.mark.unit
    async def test_health_check_contains_connections(
        self, adapter: WebSocketAdapter
    ):
        """Отвте на проверку состояния содержит количество подключений."""
        result = await adapter._health_check()
        assert "connections" in result

    @pytest.mark.unit
    async def test_health_check_connections_zero_initially(
        self, adapter: WebSocketAdapter
    ):
        """Когда подключений нет, количество будет 0."""
        result = await adapter._health_check()
        assert result["connections"] == 0

    @pytest.mark.unit
    async def test_health_check_connections_reflects_active(
        self, adapter: WebSocketAdapter
    ):
        """В ответе количество подключений соответствует активным."""
        mock_ws = AsyncMock()
        adapter._connections["fake-dev"] = mock_ws
        result = await adapter._health_check()
        assert result["connections"] == 1
        del adapter._connections["fake-dev"]
