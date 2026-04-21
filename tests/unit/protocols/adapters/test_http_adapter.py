"""Тесты для HTTPAdapter."""
import pytest
from unittest.mock import AsyncMock, patch
from aiohttp.test_utils import TestClient
from http import HTTPStatus
from typing import Any
from protocols.adapters.http_adapter import HTTPAdapter
from config.topics import TopicKey, TopicManager
from core.message_bus import MessageBus
from models.message import Message, MessageType
from models.device import ProtocolType
from tests.conftest import (
    DEVICE_DEF_ID, drain
)


class TestHTTPAdapter:
    """Тесты для HTTP адаптера."""

    class TestProtocolName:
        """Тесты свойства protocol_name."""

        @pytest.mark.unit
        def test_returns_http(self, http_adapter: HTTPAdapter):
            """protocol_name возвращает строку."""
            assert http_adapter.protocol_name == ProtocolType.HTTP.value

        @pytest.mark.unit
        def test_protocol_type_is_http(self, http_adapter: HTTPAdapter):
            """protocol_type возвращает ProtocolType.HTTP."""
            assert http_adapter.protocol_type == ProtocolType.HTTP

    class TestLifecycle:
        """Тесты жизненного цикла адаптера."""

        @pytest.mark.unit
        async def test_start_sets_running(self, http_adapter: HTTPAdapter):
            """После start() флаги _running и is_running равны True."""
            mock_runner = AsyncMock()
            mock_site = AsyncMock()

            with (
                patch('aiohttp.web.AppRunner', return_value=mock_runner),
                patch('aiohttp.web.TCPSite', return_value=mock_site),
            ):
                await http_adapter.start()
                assert http_adapter._running is True
                assert http_adapter.is_running is True
                await http_adapter.stop()

        @pytest.mark.unit
        async def test_stop_clears_running(self, http_adapter: HTTPAdapter):
            """После stop() флаги _running и is_running равны False."""
            mock_runner = AsyncMock()
            mock_site = AsyncMock()

            with (
                patch('aiohttp.web.AppRunner', return_value=mock_runner),
                patch('aiohttp.web.TCPSite', return_value=mock_site),
            ):
                await http_adapter.start()
                await http_adapter.stop()
                assert http_adapter._running is False
                assert http_adapter.is_running is False

        @pytest.mark.unit
        def test_initially_not_running(self, http_adapter: HTTPAdapter):
            """Новый адаптер не запущен."""
            assert http_adapter.is_running is False

    class TestHandleIngest:
        """Тесты обработчика телеметрии _handle_ingest."""

        @pytest.mark.unit
        async def test_valid_payload_returns_202(
            self,
            http_client:
            TestClient,
            http_url_telemetry: str,
            telemetry_body: dict[str, Any]
        ):
            """Корректный запрос телеметрии возвращает 202 ACCEPTED."""
            resp = await http_client.post(
                http_url_telemetry,
                json=telemetry_body,
            )
            assert resp.status == HTTPStatus.ACCEPTED

        @pytest.mark.unit
        async def test_response_contains_status_accepted(
            self,
            http_client:
            TestClient,
            http_url_telemetry: str,
            telemetry_body: dict[str, Any]
        ):
            """Тело успешного ответа содержит status='accepted'."""
            resp = await http_client.post(
                http_url_telemetry,
                json=telemetry_body,
            )
            data = await resp.json()
            assert data['status'] == 'accepted'

        @pytest.mark.unit
        async def test_response_contains_message_id(
            self,
            http_client: TestClient,
            http_url_telemetry: str,
            telemetry_body: dict[str, Any]
        ):
            """Тело успешного ответа содержит поле message_id."""
            resp = await http_client.post(
                http_url_telemetry,
                json=telemetry_body,
            )
            data = await resp.json()
            assert 'message_id' in data

        @pytest.mark.unit
        async def test_response_contains_timestamp(
            self,
            http_client: TestClient,
            http_url_telemetry: str,
            telemetry_body: dict[str, Any]
        ):
            """Тело успешного ответа содержит поле timestamp."""
            resp = await http_client.post(
                http_url_telemetry,
                json=telemetry_body,
            )
            data = await resp.json()
            assert 'timestamp' in data

        @pytest.mark.unit
        async def test_missing_device_id_returns_400(
            self, http_client: TestClient, http_url_telemetry: str
        ):
            """Запрос без device_id возвращает 400 BAD_REQUEST."""
            resp = await http_client.post(
                http_url_telemetry,
                json={'payload': {'test': 'test'}},
            )
            assert resp.status == HTTPStatus.BAD_REQUEST

        @pytest.mark.unit
        async def test_missing_device_id_error_status(
            self, http_client: TestClient, http_url_telemetry: str
        ):
            """При отсутствии device_id тело ответа содержит status='error'."""
            resp = await http_client.post(
                http_url_telemetry,
                json={'payload': {'test': 'test'}},
            )
            data = await resp.json()
            assert data.get('status') == 'error'

        @pytest.mark.unit
        async def test_missing_device_id_error_code(
            self, http_client: TestClient, http_url_telemetry: str
        ):
            """При отсутствии device_id error_code='MISSING_DEVICE_ID'."""
            resp = await http_client.post(
                http_url_telemetry,
                json={'payload': {'test': 'test'}},
            )
            data = await resp.json()
            assert data.get('error_code') == 'MISSING_DEVICE_ID'

        @pytest.mark.unit
        async def test_invalid_json_returns_400(
            self, http_client: TestClient, http_url_telemetry: str
        ):
            """Некорректный JSON в запросе возвращает 400 BAD_REQUEST."""
            resp = await http_client.post(
                http_url_telemetry,
                data='not-json',
                headers={'Content-Type': 'application/json'},
            )
            assert resp.status == HTTPStatus.BAD_REQUEST

        @pytest.mark.unit
        async def test_invalid_json_error_code(
            self, http_client: TestClient, http_url_telemetry: str
        ):
            """При некорректном JSON error_code='INVALID_JSON'."""
            resp = await http_client.post(
                http_url_telemetry,
                data='not-json',
                headers={'Content-Type': 'application/json'},
            )
            data = await resp.json()
            assert data.get('error_code') == 'INVALID_JSON'

        @pytest.mark.unit
        async def test_message_published_to_bus(
            self,
            topics: TopicManager,
            http_client: TestClient,
            running_bus: MessageBus,
            http_url_telemetry: str,
            telemetry_body: dict[str, Any]
        ):
            """После корректного запроса сообщение оказывается в шине."""
            received: list[Message] = []

            async def _handler(msg: Message) -> None:
                received.append(msg)

            running_bus.subscribe(topics.get_subscription_pattern(
                TopicKey.DEVICES_TELEMETRY
            ), _handler)

            await http_client.post(
                http_url_telemetry,
                json=telemetry_body,
            )
            await drain(running_bus)

            assert len(received) == 1

        @pytest.mark.unit
        async def test_published_message_has_correct_device_id(
            self,
            topics: TopicManager,
            http_client: TestClient,
            running_bus: MessageBus,
            http_url_telemetry: str,
            telemetry_body: dict[str, Any]
        ):
            """Опубликованное сообщение имеет правильный device_id."""
            received: list[Message] = []

            async def _handler(msg: Message) -> None:
                received.append(msg)

            running_bus.subscribe(topics.get_subscription_pattern(
                TopicKey.DEVICES_TELEMETRY
            ), _handler)

            await http_client.post(
                http_url_telemetry,
                json=telemetry_body,
            )
            await drain(running_bus)

            assert received[0].device_id == DEVICE_DEF_ID

        @pytest.mark.unit
        async def test_published_message_type_is_telemetry(
            self,
            topics: TopicManager,
            http_client: TestClient,
            running_bus: MessageBus,
            http_url_telemetry: str,
            telemetry_body: dict[str, Any]
        ):
            """Опубликованное сообщение имеет тип TELEMETRY."""
            received: list[Message] = []

            async def _handler(msg: Message) -> None:
                received.append(msg)

            running_bus.subscribe(topics.get_subscription_pattern(
                TopicKey.DEVICES_TELEMETRY
            ), _handler)

            await http_client.post(
                http_url_telemetry,
                json=telemetry_body,
            )
            await drain(running_bus)

            assert received[0].message_type == MessageType.TELEMETRY

        @pytest.mark.unit
        async def test_published_message_topic_matches_url(
            self,
            topics: TopicManager,
            http_client: TestClient,
            running_bus: MessageBus,
            http_url_telemetry: str,
            telemetry_body: dict[str, Any]
        ):
            """message_topic сообщения совпадает с URL эндпоинта."""
            received: list[Message] = []

            async def _handler(m: Message) -> None:
                received.append(m)

            sub_topic = topics.get_subscription_pattern(
                TopicKey.DEVICES_TELEMETRY
            )
            running_bus.subscribe(sub_topic, _handler)

            await http_client.post(
                http_url_telemetry,
                json=telemetry_body,
            )
            await drain(running_bus)

            topic = topics.get(
                TopicKey.DEVICES_TELEMETRY,
                device_id=DEVICE_DEF_ID
            )
            assert received[0].message_topic == topic

        @pytest.mark.unit
        async def test_published_message_payload_matches(
            self,
            topics: TopicManager,
            http_client: TestClient,
            running_bus: MessageBus,
            http_url_telemetry: str,
        ):
            """Нагрузка сообщения совпадает с переданным в запросе."""
            received: list[Message] = []
            device_id = 'dev-payload'
            payload = {'temp': 36.6, 'hum': 60}

            async def _handler(m: Message) -> None:
                received.append(m)

            running_bus.subscribe(topics.get_subscription_pattern(
                TopicKey.DEVICES_TELEMETRY
            ), _handler)

            await http_client.post(
                http_url_telemetry,
                json={'device_id': device_id, 'payload': payload},
            )
            await drain(running_bus)

            assert received[0].payload == payload

        @pytest.mark.unit
        async def test_rejected_message_returns_422(
            self,
            topics: TopicManager,
            http_client: TestClient,
            running_bus: MessageBus,
            http_url_telemetry: str,
        ):
            """Если шина вернула rejected, ответ — 422 UNPROCESSABLE_ENTITY."""
            device_id = 'dev-reject'

            async def _reject_handler(msg: Message) -> None:
                rejected = Message(
                    message_id=msg.message_id,
                    device_id=device_id,
                    metadata={
                        'reject_reason': 'filtered',
                        'reject_stage': 'pipeline',
                    },
                )
                await running_bus.publish(
                    topics.get(
                        TopicKey.REJECTED_TELEMETRY,
                        device_id=device_id
                    ), rejected
                )

            running_bus.subscribe(topics.get_subscription_pattern(
                TopicKey.DEVICES_TELEMETRY
            ), _reject_handler)

            resp = await http_client.post(
                http_url_telemetry,
                json={'device_id': device_id, 'payload': {}},
            )
            assert resp.status == HTTPStatus.UNPROCESSABLE_ENTITY

        @pytest.mark.unit
        async def test_rejected_message_body_status(
            self,
            topics: TopicManager,
            http_client: TestClient,
            running_bus: MessageBus,
            http_url_telemetry: str,
        ):
            """При rejected-ответе тело содержит status='rejected'."""
            device_id = 'dev-reject-body'

            async def _reject_handler(msg: Message) -> None:
                rejected = Message(
                    message_id=msg.message_id,
                    device_id=device_id,
                    metadata={
                        'reject_reason': 'validation_failed',
                        'reject_stage': 'pipeline',
                    },
                )
                await running_bus.publish(
                    topics.get(
                        TopicKey.REJECTED_TELEMETRY,
                        device_id=device_id
                    ), rejected
                )

            running_bus.subscribe(topics.get_subscription_pattern(
                TopicKey.DEVICES_TELEMETRY
            ), _reject_handler)

            resp = await http_client.post(
                http_url_telemetry,
                json={'device_id': device_id, 'payload': {}},
            )
            data = await resp.json()
            assert data['status'] == 'rejected'

    class TestHandleRegister:
        """Тесты обработчика регистрации _handle_register."""

        @pytest.mark.unit
        async def test_valid_register_returns_201(
            self, http_client: TestClient, http_url_register: str
        ):
            """Корректный запрос регистрации возвращает 201 CREATED."""
            resp = await http_client.post(
                http_url_register,
                json={'device_id': DEVICE_DEF_ID, 'name': 'Sensor A'},
            )
            assert resp.status == HTTPStatus.CREATED

        @pytest.mark.unit
        async def test_valid_register_status_registered(
            self, http_client: TestClient, http_url_register: str
        ):
            """Тело ответа на регистрацию содержит status='registered'."""
            resp = await http_client.post(
                http_url_register,
                json={'device_id': DEVICE_DEF_ID, 'name': 'Sensor A'},
            )
            data = await resp.json()
            assert data['status'] == 'registered'

        @pytest.mark.unit
        async def test_valid_register_contains_message_id(
            self, http_client: TestClient, http_url_register: str
        ):
            """Тело ответа на регистрацию содержит поле message_id."""
            resp = await http_client.post(
                http_url_register,
                json={'device_id': DEVICE_DEF_ID, 'name': 'Sensor A'},
            )
            data = await resp.json()
            assert 'message_id' in data

        @pytest.mark.unit
        async def test_missing_device_id_returns_400(
            self, http_client: TestClient, http_url_register: str
        ):
            """Запрос регистрации без device_id возвращает 400 BAD_REQUEST."""
            resp = await http_client.post(
                http_url_register,
                json={'name': 'Sensor A'},
            )
            assert resp.status == HTTPStatus.BAD_REQUEST

        @pytest.mark.unit
        async def test_missing_device_id_error_code(
            self, http_client: TestClient, http_url_register: str
        ):
            """При отсутствии device_id error_code='MISSING_DEVICE_ID'."""
            resp = await http_client.post(
                http_url_register,
                json={'name': 'Sensor A'},
            )
            data = await resp.json()
            assert data.get('error_code') == 'MISSING_DEVICE_ID'

        @pytest.mark.unit
        async def test_invalid_json_returns_400(
            self, http_client: TestClient, http_url_register: str
        ):
            """Некорректный JSON при регистрации возвращает BAD_REQUEST."""
            resp = await http_client.post(
                http_url_register,
                data='bad',
                headers={'Content-Type': 'application/json'},
            )
            assert resp.status == HTTPStatus.BAD_REQUEST

        @pytest.mark.unit
        async def test_invalid_json_error_code(
            self, http_client: TestClient, http_url_register: str
        ):
            """При некорректном JSON error_code='INVALID_JSON'."""
            resp = await http_client.post(
                http_url_register,
                data='bad',
                headers={'Content-Type': 'application/json'},
            )
            data = await resp.json()
            assert data.get('error_code') == 'INVALID_JSON'

        @pytest.mark.unit
        async def test_register_published_to_bus(
            self,
            topics: TopicManager,
            http_client: TestClient,
            running_bus: MessageBus,
            http_url_register: str,
        ):
            """После регистрации сообщение появляется в шине."""
            received: list[Message] = []

            async def _handler(msg: Message) -> None:
                received.append(msg)

            running_bus.subscribe(
                topics.get_subscription_pattern(
                    TopicKey.DEVICES_REGISTER
                ), _handler
            )

            await http_client.post(
                http_url_register,
                json={'device_id': DEVICE_DEF_ID, 'name': 'Sensor A'},
            )
            await drain(running_bus)

            assert len(received) == 1

        @pytest.mark.unit
        async def test_register_message_type_is_registration(
            self,
            topics: TopicManager,
            http_client: TestClient,
            running_bus: MessageBus,
            http_url_register: str,
        ):
            """Сообщение регистрации имеет тип REGISTRATION."""
            received: list[Message] = []

            async def _handler(msg: Message) -> None:
                received.append(msg)

            running_bus.subscribe(
                topics.get_subscription_pattern(
                    TopicKey.DEVICES_REGISTER
                ), _handler
            )

            await http_client.post(
                http_url_register,
                json={'device_id': DEVICE_DEF_ID, 'name': 'Sensor A'},
            )
            await drain(running_bus)

            assert received[0].message_type == MessageType.REGISTRATION

    class TestHandleHealth:
        """Тесты обработчика проверки состояния _handle_health."""

        @pytest.mark.unit
        async def test_health_returns_200(
            self, http_client: TestClient, http_url_health: str
        ):
            """GET /health возвращает 200 OK."""
            resp = await http_client.get(http_url_health)
            assert resp.status == HTTPStatus.OK

        @pytest.mark.unit
        async def test_health_contains_protocol(
            self, http_client: TestClient, http_url_health: str
        ):
            """Тело ответа health содержит ключ 'protocol'."""
            resp = await http_client.get(http_url_health)
            data = await resp.json()
            assert 'protocol' in data

        @pytest.mark.unit
        async def test_health_contains_running(
            self, http_client: TestClient, http_url_health: str
        ):
            """Тело ответа health содержит ключ 'running'."""
            resp = await http_client.get(http_url_health)
            data = await resp.json()
            assert 'running' in data

        @pytest.mark.unit
        async def test_health_protocol_is_http(
            self, http_client: TestClient, http_url_health: str
        ):
            """Поле protocol в health равно 'HTTP'."""
            resp = await http_client.get(http_url_health)
            data = await resp.json()
            assert data['protocol'] == 'HTTP'

        @pytest.mark.unit
        async def test_health_running_is_true(
            self, http_client: TestClient, http_url_health: str
        ):
            """Поле running в health равно True, когда адаптер запущен."""
            resp = await http_client.get(http_url_health)
            data = await resp.json()
            assert data['running'] is True
