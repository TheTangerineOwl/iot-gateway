"""Тесты для WebSocketAdapter."""
import asyncio
import json
import pytest
from aiohttp.test_utils import TestClient
from http import HTTPStatus
from unittest.mock import AsyncMock, patch
from protocols.adapters.websocket_adapter import WebSocketAdapter
from core.message_bus import MessageBus
from models.message import MessageType, Message
from models.device import ProtocolType
from tests.conftest import (
    drain,
    not_raises,
    DEVICE_DEF_ID,
    TOPIC_TELEMETRY_WC,
    TOPIC_TELEMETRY,
    TOPIC_REGISTER_WC,
    TOPIC_REGISTER,
)
from tests.unit.protocols.adapters.conftest import (
    WS_TELEMETRY_BODY,
    WS_HEARTBEAT_BODY,
    WS_REGISTER_BODY,
    HTTP_REGISTER_BODY,
)


async def _ws_exchange(
    ws_client: TestClient,
    url: str,
    messages: list[dict],
) -> list[dict]:
    """
    Вспомогательная функция для теста соединений.

    Открыть WS-соединение, последовательно отправить сообщения,
    собрать ответы и закрыть соединение.
    """
    responses = []
    async with ws_client.ws_connect(url) as ws:
        for msg in messages:
            await ws.send_str(json.dumps(msg))
            resp = await asyncio.wait_for(ws.receive_json(), timeout=2.0)
            responses.append(resp)
    return responses


class TestWebSocketAdapter:
    """Тесты WebSocketAdapter."""

    class TestProtocolName:
        """Тест имени и типа протокола."""

        @pytest.mark.unit
        def test_protocol_name_is_websocket(
            self, ws_adapter: WebSocketAdapter
        ):
            """protocol_name возвращает 'WebSocket'."""
            assert ws_adapter.protocol_name == ProtocolType.WEBSOCKET.value

        @pytest.mark.unit
        def test_protocol_type_is_websocket(
            self, ws_adapter: WebSocketAdapter
        ):
            """protocol_type возвращает ProtocolType.WEBSOCKET."""
            assert ws_adapter.protocol_type == ProtocolType.WEBSOCKET

    class TestLifecycle:
        """Тесты жизненного цикла адаптера."""

        @pytest.mark.unit
        async def test_start_sets_running(
            self, ws_adapter: WebSocketAdapter
        ):
            """После start() флаг _running=True."""
            with (
                patch('aiohttp.web.AppRunner') as mock_runner,
                patch('aiohttp.web.TCPSite') as mock_site,
            ):
                mock_runner.return_value.setup = AsyncMock()
                mock_site.return_value.start = AsyncMock()
                mock_runner.return_value.cleanup = AsyncMock()

                await ws_adapter.start()
                assert ws_adapter._running is True
                await ws_adapter.stop()

        @pytest.mark.unit
        async def test_stop_clears_running(
            self, ws_adapter: WebSocketAdapter
        ):
            """После stop() флаг _running=False."""
            with (
                patch('aiohttp.web.AppRunner') as mock_runner,
                patch('aiohttp.web.TCPSite') as mock_site,
            ):
                mock_runner.return_value.setup = AsyncMock()
                mock_site.return_value.start = AsyncMock()
                mock_runner.return_value.cleanup = AsyncMock()

                await ws_adapter.start()
                await ws_adapter.stop()
                assert ws_adapter._running is False

        @pytest.mark.unit
        async def test_stop_closes_active_connections(
            self, ws_adapter: WebSocketAdapter
        ):
            """stop() закрывает все активные соединения и очищает словарь."""
            mock_ws = AsyncMock()
            mock_ws.close = AsyncMock()
            ws_adapter._connections['dev-x'] = mock_ws

            with (
                patch('aiohttp.web.AppRunner') as mock_runner,
                patch('aiohttp.web.TCPSite') as mock_site,
            ):
                mock_runner.return_value.setup = AsyncMock()
                mock_site.return_value.start = AsyncMock()
                mock_runner.return_value.cleanup = AsyncMock()

                await ws_adapter.start()
                await ws_adapter.stop()

            mock_ws.close.assert_awaited_once()
            assert ws_adapter._connections == {}

        @pytest.mark.unit
        async def test_stop_with_failing_close_does_not_raise(
            self, ws_adapter: WebSocketAdapter
        ):
            """stop() не пробрасывает исключение при ошибке закрытия."""
            mock_ws = AsyncMock()
            mock_ws.close = AsyncMock(side_effect=RuntimeError('boom'))
            ws_adapter._connections['err-dev'] = mock_ws

            with (
                patch('aiohttp.web.AppRunner') as mock_runner,
                patch('aiohttp.web.TCPSite') as mock_site,
            ):
                mock_runner.return_value.setup = AsyncMock()
                mock_site.return_value.start = AsyncMock()
                mock_runner.return_value.cleanup = AsyncMock()

                await ws_adapter.start()
                with not_raises(Exception):
                    await ws_adapter.stop()

            assert ws_adapter._connections == {}

        @pytest.mark.unit
        async def test_stop_without_start_does_not_raise(
            self, ws_adapter: WebSocketAdapter
        ):
            """stop() без предварительного start() не бросает исключений."""
            with not_raises(Exception):
                await ws_adapter.stop()
            assert ws_adapter._running is False

    class TestWsTelemetry:
        """Тесты WS-обработки телеметрии."""

        @pytest.mark.unit
        async def test_telemetry_returns_accepted(
            self,
            ws_client: TestClient,
            ws_url_telemetry: str,
        ):
            """Ответ на корректную телеметрию содержит status='accepted'."""
            responses = await _ws_exchange(
                ws_client, ws_url_telemetry, [WS_TELEMETRY_BODY]
            )
            assert responses[0]['status'] == 'accepted'

        @pytest.mark.unit
        async def test_telemetry_response_contains_message_id(
            self,
            ws_client: TestClient,
            ws_url_telemetry: str,
        ):
            """Ответ на телеметрию содержит поле message_id."""
            responses = await _ws_exchange(
                ws_client, ws_url_telemetry, [WS_TELEMETRY_BODY]
            )
            assert 'message_id' in responses[0]

        @pytest.mark.unit
        async def test_telemetry_response_contains_timestamp(
            self,
            ws_client: TestClient,
            ws_url_telemetry: str,
        ):
            """Ответ на телеметрию содержит поле timestamp."""
            responses = await _ws_exchange(
                ws_client, ws_url_telemetry, [WS_TELEMETRY_BODY]
            )
            assert 'timestamp' in responses[0]

        @pytest.mark.unit
        async def test_telemetry_publishes_to_bus(
            self,
            ws_client: TestClient,
            ws_url_telemetry: str,
            running_bus: MessageBus,
        ):
            """Телеметрия публикуется с правильным типом и device_id."""
            received: list[Message] = []

            async def _handler(msg):
                received.append(msg)

            running_bus.subscribe(
                TOPIC_TELEMETRY % DEVICE_DEF_ID,
                lambda m: _handler(m),
            )
            await _ws_exchange(
                ws_client,
                ws_url_telemetry,
                [WS_TELEMETRY_BODY]
            )
            await drain(running_bus)

            assert len(received) == 1
            assert received[0].message_type == MessageType.TELEMETRY
            assert received[0].device_id == DEVICE_DEF_ID

        @pytest.mark.unit
        async def test_telemetry_message_topic(
            self,
            ws_client: TestClient,
            ws_url_telemetry: str,
            running_bus: MessageBus,
        ):
            """Топик сообщения соответствует шаблону telemetry.{device_id}."""
            received: list[Message] = []

            async def _handler(msg):
                received.append(msg)

            running_bus.subscribe(
                TOPIC_TELEMETRY_WC,
                lambda m: _handler(m),
            )
            await _ws_exchange(
                ws_client,
                ws_url_telemetry,
                [WS_TELEMETRY_BODY]
            )
            await drain(running_bus)

            assert received[0].message_topic == TOPIC_TELEMETRY % DEVICE_DEF_ID

        @pytest.mark.unit
        async def test_telemetry_protocol_set_to_websocket(
            self,
            ws_client: TestClient,
            ws_url_telemetry: str,
            running_bus: MessageBus,
        ):
            """Сообщение на шине имеет protocol=WEBSOCKET."""
            received: list[Message] = []

            async def _handler(msg):
                received.append(msg)

            running_bus.subscribe(
                TOPIC_TELEMETRY_WC,
                lambda m: _handler(m),
            )
            await _ws_exchange(
                ws_client,
                ws_url_telemetry,
                [WS_TELEMETRY_BODY]
            )
            await drain(running_bus)

            assert received[0].protocol == ProtocolType.WEBSOCKET

        @pytest.mark.unit
        async def test_telemetry_default_type_when_omitted(
            self,
            ws_client: TestClient,
            ws_url_telemetry: str,
            running_bus: MessageBus,
        ):
            """Без поля message_type сообщение трактуется как telemetry."""
            received: list[Message] = []

            async def _handler(msg):
                received.append(msg)

            running_bus.subscribe(
                TOPIC_TELEMETRY_WC,
                lambda m: _handler(m),
            )
            await _ws_exchange(
                ws_client,
                ws_url_telemetry,
                [{'device_id': DEVICE_DEF_ID, 'payload': {'x': 1}}],
            )
            await drain(running_bus)

            assert len(received) == 1
            assert received[0].message_type == MessageType.TELEMETRY

    class TestWsHeartbeat:
        """Тесты WS-обработки heartbeat."""

        @pytest.mark.unit
        async def test_heartbeat_returns_ok(
            self,
            ws_client: TestClient,
            ws_url_telemetry: str,
        ):
            """Ответ на heartbeat содержит status='ok'."""
            responses = await _ws_exchange(
                ws_client, ws_url_telemetry, [WS_HEARTBEAT_BODY]
            )
            assert responses[0]['status'] == 'ok'

        @pytest.mark.unit
        async def test_heartbeat_publishes_to_bus(
            self,
            ws_client: TestClient,
            ws_url_telemetry: str,
            running_bus: MessageBus,
        ):
            """Сердцебиение публикуется с правильным типом и device_id."""
            received: list[Message] = []

            async def _handler(msg):
                received.append(msg)

            running_bus.subscribe(
                'device.heartbeat.*',
                lambda m: _handler(m),
            )
            await _ws_exchange(
                ws_client,
                ws_url_telemetry,
                [WS_HEARTBEAT_BODY]
            )
            await drain(running_bus)

            assert len(received) == 1
            assert received[0].message_type == MessageType.HEARTBEAT
            assert received[0].device_id == DEVICE_DEF_ID

        @pytest.mark.unit
        async def test_heartbeat_message_topic(
            self,
            ws_client: TestClient,
            ws_url_telemetry: str,
            running_bus: MessageBus,
        ):
            """Топик heartbeat соответствует 'device.heartbeat.{device_id}'."""
            received: list[Message] = []

            async def _handler(msg):
                received.append(msg)

            running_bus.subscribe(
                'device.heartbeat.*',
                lambda m: _handler(m),
            )
            await _ws_exchange(
                ws_client,
                ws_url_telemetry,
                [WS_HEARTBEAT_BODY]
            )
            await drain(running_bus)

            assert (
                received[0].message_topic
                == f'device.heartbeat.{DEVICE_DEF_ID}'
            )

    class TestWsRegister:
        """Тесты WS-регистрации."""

        @pytest.mark.unit
        async def test_register_returns_registered(
            self,
            ws_client: TestClient,
            ws_url_register: str,
        ):
            """Ответ на WS-регистрацию содержит status='registered'."""
            responses = await _ws_exchange(
                ws_client, ws_url_register, [WS_REGISTER_BODY]
            )
            assert responses[0]['status'] == 'registered'

        @pytest.mark.unit
        async def test_register_publishes_to_bus(
            self,
            ws_client: TestClient,
            ws_url_register: str,
            running_bus: MessageBus,
        ):
            """WS-регистрация публикуется с правильным типом и device_id."""
            received: list[Message] = []

            async def _handler(msg):
                received.append(msg)

            running_bus.subscribe(
                TOPIC_REGISTER_WC,
                lambda m: _handler(m),
            )
            await _ws_exchange(ws_client, ws_url_register, [WS_REGISTER_BODY])
            await drain(running_bus)

            assert len(received) == 1
            assert received[0].message_type == MessageType.REGISTRATION
            assert received[0].device_id == DEVICE_DEF_ID

        @pytest.mark.unit
        async def test_register_message_topic(
            self,
            ws_client: TestClient,
            ws_url_register: str,
            running_bus: MessageBus,
        ):
            """Топик регистрации соответствует device.register.{device_id}."""
            received: list[Message] = []

            async def _handler(msg):
                received.append(msg)

            running_bus.subscribe(
                TOPIC_REGISTER_WC,
                lambda m: _handler(m),
            )
            await _ws_exchange(ws_client, ws_url_register, [WS_REGISTER_BODY])
            await drain(running_bus)

            assert received[0].message_topic == TOPIC_REGISTER % DEVICE_DEF_ID

        @pytest.mark.unit
        async def test_register_response_contains_message_id(
            self,
            ws_client: TestClient,
            ws_url_register: str,
        ):
            """Ответ на WS-регистрацию содержит поле message_id."""
            responses = await _ws_exchange(
                ws_client, ws_url_register, [WS_REGISTER_BODY]
            )
            assert 'message_id' in responses[0]

    class TestWsErrors:
        """Тесты WS-ответов на некорректный ввод."""

        @pytest.mark.unit
        async def test_invalid_json_returns_error_status(
            self,
            ws_client: TestClient,
            ws_url_telemetry: str,
        ):
            """Некорректный JSON возвращает status='error'."""
            async with ws_client.ws_connect(ws_url_telemetry) as ws:
                await ws.send_str('this is not json{{{')
                resp = await asyncio.wait_for(ws.receive_json(), timeout=2.0)
            assert resp.get('status') == 'error'

        @pytest.mark.unit
        async def test_invalid_json_returns_error_code(
            self,
            ws_client: TestClient,
            ws_url_telemetry: str,
        ):
            """Некорректный JSON возвращает error_code='INVALID_JSON'."""
            async with ws_client.ws_connect(ws_url_telemetry) as ws:
                await ws.send_str('>>')
                resp = await asyncio.wait_for(ws.receive_json(), timeout=2.0)
            assert resp.get('error_code') == 'INVALID_JSON'

        @pytest.mark.unit
        async def test_missing_device_id_returns_error_status(
            self,
            ws_client: TestClient,
            ws_url_telemetry: str,
        ):
            """Отсутствие device_id возвращает status='error'."""
            async with ws_client.ws_connect(ws_url_telemetry) as ws:
                await ws.send_str(
                    json.dumps({'message_type': 'telemetry', 'payload': {}})
                )
                resp = await asyncio.wait_for(ws.receive_json(), timeout=2.0)
            assert resp.get('status') == 'error'

        @pytest.mark.unit
        async def test_missing_device_id_returns_error_code(
            self,
            ws_client: TestClient,
            ws_url_telemetry: str,
        ):
            """Отсутствие device_id возвращает MISSING_DEVICE_ID."""
            async with ws_client.ws_connect(ws_url_telemetry) as ws:
                await ws.send_str(json.dumps({'message_type': 'telemetry'}))
                resp = await asyncio.wait_for(ws.receive_json(), timeout=2.0)
            assert resp.get('error_code') == 'MISSING_DEVICE_ID'

        @pytest.mark.unit
        async def test_unknown_message_type_returns_error_status(
            self,
            ws_client: TestClient,
            ws_url_telemetry: str,
        ):
            """Неизвестный message_type возвращает status='error'."""
            responses = await _ws_exchange(
                ws_client,
                ws_url_telemetry,
                [{'message_type': 'unknown_type', 'device_id': DEVICE_DEF_ID}],
            )
            assert responses[0].get('status') == 'error'

        @pytest.mark.unit
        async def test_unknown_message_type_returns_error_code(
            self,
            ws_client: TestClient,
            ws_url_telemetry: str,
        ):
            """Неизвестный message_type возвращает UNKNOWN_TYPE."""
            responses = await _ws_exchange(
                ws_client,
                ws_url_telemetry,
                [{'message_type': 'unknown_type', 'device_id': DEVICE_DEF_ID}],
            )
            assert responses[0].get('error_code') == 'UNKNOWN_TYPE'

        @pytest.mark.unit
        async def test_empty_device_id_string_returns_error(
            self,
            ws_client: TestClient,
            ws_url_telemetry: str,
        ):
            """Пустая строка в device_id обрабатывается как без id."""
            async with ws_client.ws_connect(ws_url_telemetry) as ws:
                await ws.send_str(
                    json.dumps({'message_type': 'telemetry', 'device_id': ''})
                )
                resp = await asyncio.wait_for(ws.receive_json(), timeout=2.0)
            assert resp.get('status') == 'error'
            assert resp.get('error_code') == 'MISSING_DEVICE_ID'

    class TestWsConnections:
        """Тесты управления WS-соединениями."""

        @pytest.mark.unit
        async def test_connection_registered_after_first_message(
            self,
            ws_client: TestClient,
            ws_adapter: WebSocketAdapter,
            ws_url_telemetry: str,
        ):
            """После первого сообщения device_id появляется в _connections."""
            async with ws_client.ws_connect(ws_url_telemetry) as ws:
                await ws.send_str(json.dumps(WS_TELEMETRY_BODY))
                await asyncio.wait_for(ws.receive_json(), timeout=2.0)
                assert DEVICE_DEF_ID in ws_adapter._connections

        @pytest.mark.unit
        async def test_connection_removed_after_close(
            self,
            ws_client: TestClient,
            ws_adapter: WebSocketAdapter,
            ws_url_telemetry: str,
        ):
            """После закрытия соединения device_id исчезает из _connections."""
            async with ws_client.ws_connect(ws_url_telemetry) as ws:
                await ws.send_str(json.dumps(WS_TELEMETRY_BODY))
                await asyncio.wait_for(ws.receive_json(), timeout=2.0)

            await asyncio.sleep(0.05)
            assert DEVICE_DEF_ID not in ws_adapter._connections

        @pytest.mark.unit
        async def test_multiple_messages_keep_single_connection_entry(
            self,
            ws_client: TestClient,
            ws_adapter: WebSocketAdapter,
            ws_url_telemetry: str,
        ):
            """Несколько сообщений от одного device_id не дублируют запись."""
            async with ws_client.ws_connect(ws_url_telemetry) as ws:
                for _ in range(3):
                    await ws.send_str(json.dumps(WS_HEARTBEAT_BODY))
                    await asyncio.wait_for(ws.receive_json(), timeout=2.0)

            count = sum(
                1 for k in ws_adapter._connections
                if k == DEVICE_DEF_ID
            )
            assert count <= 1

        @pytest.mark.unit
        async def test_connections_count_increases_with_active_ws(
            self,
            ws_client: TestClient,
            ws_adapter: WebSocketAdapter,
            ws_url_telemetry: str,
            ws_url_health: str,
        ):
            """Счётчик соединений в /health растёт при активном WS."""
            async with ws_client.ws_connect(ws_url_telemetry) as ws:
                await ws.send_str(json.dumps(WS_HEARTBEAT_BODY))
                await asyncio.wait_for(ws.receive_json(), timeout=2.0)

                resp = await ws_client.get(ws_url_health)
                data = await resp.json()
            assert data['connections'] >= 1

    class TestHttpRegister:
        """Тесты HTTP-регистрации устройства."""

        @pytest.mark.unit
        async def test_valid_register_returns_201(
            self,
            ws_client: TestClient,
            ws_url_register: str,
        ):
            """Корректный запрос возвращает 201 CREATED."""
            resp = await ws_client.post(
                ws_url_register,
                json=HTTP_REGISTER_BODY
            )
            assert resp.status == HTTPStatus.CREATED

        @pytest.mark.unit
        async def test_valid_register_body_contains_status_registered(
            self,
            ws_client: TestClient,
            ws_url_register: str,
        ):
            """Тело ответа содержит status='registered'."""
            resp = await ws_client.post(
                ws_url_register,
                json=HTTP_REGISTER_BODY
            )
            data = await resp.json()
            assert data['status'] == 'registered'

        @pytest.mark.unit
        async def test_valid_register_body_contains_message_id(
            self,
            ws_client: TestClient,
            ws_url_register: str,
        ):
            """Тело ответа содержит поле message_id."""
            resp = await ws_client.post(
                ws_url_register,
                json=HTTP_REGISTER_BODY
            )
            data = await resp.json()
            assert 'message_id' in data

        @pytest.mark.unit
        async def test_invalid_json_returns_400(
            self,
            ws_client: TestClient,
            ws_url_register: str,
        ):
            """Некорректный JSON в теле запроса возвращает 400 BAD REQUEST."""
            resp = await ws_client.post(
                ws_url_register,
                data='bad-json',
                headers={'Content-Type': 'application/json'},
            )
            assert resp.status == HTTPStatus.BAD_REQUEST

        @pytest.mark.unit
        async def test_invalid_json_body_contains_error_status(
            self,
            ws_client: TestClient,
            ws_url_register: str,
        ):
            """Тело ответа на некорректный JSON содержит status='error'."""
            resp = await ws_client.post(
                ws_url_register,
                data='bad-json',
                headers={'Content-Type': 'application/json'},
            )
            data = await resp.json()
            assert data.get('status') == 'error'

        @pytest.mark.unit
        async def test_invalid_json_body_contains_error_code(
            self,
            ws_client: TestClient,
            ws_url_register: str,
        ):
            """Ответ некорректный JSON содержит error_code='INVALID_JSON'."""
            resp = await ws_client.post(
                ws_url_register,
                data='bad-json',
                headers={'Content-Type': 'application/json'},
            )
            data = await resp.json()
            assert data.get('error_code') == 'INVALID_JSON'

        @pytest.mark.unit
        async def test_publishes_registration_to_bus(
            self,
            ws_client: TestClient,
            ws_url_register: str,
            running_bus: MessageBus,
        ):
            """HTTP-регистрация публикует сообщение на шину."""
            received: list[Message] = []

            async def _handler(msg):
                received.append(msg)

            running_bus.subscribe(
                TOPIC_REGISTER_WC,
                lambda m: _handler(m),
            )
            await ws_client.post(ws_url_register, json=HTTP_REGISTER_BODY)
            await drain(running_bus)

            assert len(received) == 1
            assert received[0].message_type == MessageType.REGISTRATION
            assert received[0].device_id == DEVICE_DEF_ID

        @pytest.mark.unit
        async def test_message_topic_set_correctly(
            self,
            ws_client: TestClient,
            ws_url_register: str,
            running_bus: MessageBus,
        ):
            """Топик сообщения регистрации задаётся корректно."""
            received: list[Message] = []

            async def _handler(msg):
                received.append(msg)

            running_bus.subscribe(
                TOPIC_REGISTER_WC,
                lambda m: _handler(m),
            )
            await ws_client.post(ws_url_register, json=HTTP_REGISTER_BODY)
            await drain(running_bus)

            assert received[0].message_topic == TOPIC_REGISTER % DEVICE_DEF_ID

        @pytest.mark.unit
        async def test_registration_protocol_set_to_websocket(
            self,
            ws_client: TestClient,
            ws_url_register: str,
            running_bus: MessageBus,
        ):
            """Сообщение регистрации имеет protocol=WEBSOCKET."""
            received: list[Message] = []

            async def _handler(msg):
                received.append(msg)

            running_bus.subscribe(
                TOPIC_REGISTER_WC,
                lambda m: _handler(m),
            )
            await ws_client.post(ws_url_register, json=HTTP_REGISTER_BODY)
            await drain(running_bus)

            assert received[0].protocol == ProtocolType.WEBSOCKET

    class TestHttpHealth:
        """Тесты HTTP-эндпоинта /health."""

        @pytest.mark.unit
        async def test_health_returns_200(
            self,
            ws_client: TestClient,
            ws_url_health: str,
        ):
            """GET /health возвращает 200 OK."""
            resp = await ws_client.get(ws_url_health)
            assert resp.status == HTTPStatus.OK

        @pytest.mark.unit
        async def test_health_contains_protocol(
            self,
            ws_client: TestClient,
            ws_url_health: str,
        ):
            """Ответ /health содержит поле protocol='WebSocket'."""
            resp = await ws_client.get(ws_url_health)
            data = await resp.json()
            assert data['protocol'] == 'WebSocket'

        @pytest.mark.unit
        async def test_health_contains_running(
            self,
            ws_client: TestClient,
            ws_url_health: str,
        ):
            """Ответ /health содержит поле running."""
            resp = await ws_client.get(ws_url_health)
            data = await resp.json()
            assert 'running' in data

        @pytest.mark.unit
        async def test_health_running_true_when_adapter_running(
            self,
            ws_client: TestClient,
            ws_url_health: str,
        ):
            """Когда адаптер запущен, ответ /health содержит running=True."""
            resp = await ws_client.get(ws_url_health)
            data = await resp.json()
            assert data['running'] is True

        @pytest.mark.unit
        async def test_health_contains_connections_field(
            self,
            ws_client: TestClient,
            ws_url_health: str,
        ):
            """Ответ /health содержит поле connections."""
            resp = await ws_client.get(ws_url_health)
            data = await resp.json()
            assert 'connections' in data

        @pytest.mark.unit
        async def test_health_connections_zero_initially(
            self,
            ws_client: TestClient,
            ws_url_health: str,
        ):
            """При отсутствии подключений /health возвращает connections=0."""
            resp = await ws_client.get(ws_url_health)
            data = await resp.json()
            assert data['connections'] == 0

        @pytest.mark.unit
        async def test_health_connections_count_increases_with_active_ws(
            self,
            ws_client: TestClient,
            ws_adapter: WebSocketAdapter,
            ws_url_telemetry: str,
            ws_url_health: str,
        ):
            """Счётчик connections растёт при активном WS-соединении."""
            async with ws_client.ws_connect(ws_url_telemetry) as ws:
                await ws.send_str(json.dumps(WS_HEARTBEAT_BODY))
                await asyncio.wait_for(ws.receive_json(), timeout=2.0)

                resp = await ws_client.get(ws_url_health)
                data = await resp.json()
            assert data['connections'] >= 1

    class TestHealthCheck:
        """Тесты метода _health_check() (без HTTP)."""

        @pytest.mark.unit
        async def test_health_check_returns_dict(
            self, ws_adapter: WebSocketAdapter
        ):
            """_health_check() возвращает словарь."""
            result = await ws_adapter._health_check()
            assert isinstance(result, dict)

        @pytest.mark.unit
        async def test_health_check_protocol_name(
            self, ws_adapter: WebSocketAdapter
        ):
            """_health_check() содержит protocol='WebSocket'."""
            result = await ws_adapter._health_check()
            assert result['protocol'] == 'WebSocket'

        @pytest.mark.unit
        async def test_health_check_contains_running(
            self, ws_adapter: WebSocketAdapter
        ):
            """_health_check() содержит поле running."""
            result = await ws_adapter._health_check()
            assert 'running' in result

        @pytest.mark.unit
        async def test_health_check_running_reflects_state(
            self, ws_adapter: WebSocketAdapter
        ):
            """_health_check() отражает актуальное значение _running."""
            ws_adapter._running = True
            result = await ws_adapter._health_check()
            assert result['running'] is True

            ws_adapter._running = False
            result = await ws_adapter._health_check()
            assert result['running'] is False

        @pytest.mark.unit
        async def test_health_check_connections_zero_initially(
            self, ws_adapter: WebSocketAdapter
        ):
            """Тест _health_check() без активных соединений."""
            result = await ws_adapter._health_check()
            assert isinstance(result, dict)

        @pytest.mark.unit
        async def test_health_check_connections_reflects_active(
            self, ws_adapter: WebSocketAdapter
        ):
            """_handle_health отражает количество активных соединений."""
            mock_ws = AsyncMock()
            ws_adapter._connections['fake-dev'] = mock_ws

            health = await ws_adapter._health_check()
            health['connections'] = len(ws_adapter._connections)

            assert health['connections'] == 1
            del ws_adapter._connections['fake-dev']

    class TestHandleRejected:
        """Тесты метода _handle_rejected()."""

        @pytest.mark.unit
        async def test_handle_rejected_sends_to_open_connection(
            self, ws_adapter: WebSocketAdapter
        ):
            """_handle_rejected() отправляет сообщение открытому соединению."""
            mock_ws = AsyncMock()
            mock_ws.closed = False
            ws_adapter._connections[DEVICE_DEF_ID] = mock_ws

            msg = Message(
                device_id=DEVICE_DEF_ID,
                message_type=MessageType.TELEMETRY,
                metadata={
                    'reject_reason': 'rate_limit',
                    'reject_stage': 'filter'
                },
            )
            await ws_adapter._handle_rejected(msg)

            mock_ws.send_json.assert_awaited_once()
            sent = mock_ws.send_json.call_args[0][0]
            assert sent['status'] == 'rejected'
            assert sent['reason'] == 'rate_limit'
            assert sent['stage'] == 'filter'

            del ws_adapter._connections[DEVICE_DEF_ID]

        @pytest.mark.unit
        async def test_handle_rejected_skips_closed_connection(
            self, ws_adapter: WebSocketAdapter
        ):
            """Не отправляет ничего, если соединение закрыто."""
            mock_ws = AsyncMock()
            mock_ws.closed = True
            ws_adapter._connections[DEVICE_DEF_ID] = mock_ws

            msg = Message(
                device_id=DEVICE_DEF_ID,
                message_type=MessageType.TELEMETRY,
            )
            await ws_adapter._handle_rejected(msg)

            mock_ws.send_json.assert_not_awaited()
            del ws_adapter._connections[DEVICE_DEF_ID]

        @pytest.mark.unit
        async def test_handle_rejected_skips_unknown_device(
            self, ws_adapter: WebSocketAdapter
        ):
            """_handle_rejected() игнорирует незарегистрированный device_id."""
            msg = Message(
                device_id='ghost-device',
                message_type=MessageType.TELEMETRY,
            )
            with not_raises(Exception):
                await ws_adapter._handle_rejected(msg)

        @pytest.mark.unit
        async def test_handle_rejected_uses_default_reason(
            self, ws_adapter: WebSocketAdapter
        ):
            """Использует 'filtered' как reason по умолчанию."""
            mock_ws = AsyncMock()
            mock_ws.closed = False
            ws_adapter._connections[DEVICE_DEF_ID] = mock_ws

            msg = Message(
                device_id=DEVICE_DEF_ID,
                message_type=MessageType.TELEMETRY,
                metadata={},
            )
            await ws_adapter._handle_rejected(msg)

            sent = mock_ws.send_json.call_args[0][0]
            assert sent['reason'] == 'filtered'
            assert sent['stage'] == 'unknown'

            del ws_adapter._connections[DEVICE_DEF_ID]
