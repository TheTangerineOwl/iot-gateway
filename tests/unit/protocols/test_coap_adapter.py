"""Юнит-тесты для CoAPAdapter."""
import aiocoap
from aiocoap.numbers.contentformat import ContentFormat
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from core.message_bus import MessageBus
from core.registry import DeviceRegistry
from models.message import MessageType
from protocols.coap_adapter import (
    CoAPAdapter,
    _IngestResource,
    _RegisterResource,
    _HealthResource
)


@pytest_asyncio.fixture
async def adapter(running_bus: MessageBus, registry: DeviceRegistry):
    """WebSocket-адаптер, подключённый к шине."""
    a = CoAPAdapter()
    a.set_gateway_context(running_bus, registry)
    yield a


def make_adapter(
    bus: AsyncMock | None = None,
    registry: MagicMock | None = None
):
    """Создать CoAPAdapter с подключённой mock-шиной."""
    adapter = CoAPAdapter()
    mock_bus = bus or AsyncMock()
    mock_registry = registry or MagicMock()
    adapter.set_gateway_context(mock_bus, mock_registry)
    return adapter


def _coap_request(payload: bytes = b"") -> aiocoap.Message:
    """Сформировать минимальный CoAP-запрос с заданным payload."""
    msg = aiocoap.Message(code=aiocoap.POST, payload=payload)
    return msg


def _json_payload(data: dict) -> bytes:
    """Сериализовать словарь в байты JSON."""
    return json.dumps(data).encode()


def _parse_response(msg: aiocoap.Message) -> dict:
    """Десериализовать payload ответа из JSON."""
    return json.loads(msg.payload.decode())


@pytest.mark.unit
class TestCoAPAdapterProperties:
    """Проверяет базовые свойства адаптера."""

    def test_protocol_name(self, adapter: CoAPAdapter):
        """Возвращается имя протокола CoAP."""
        assert adapter.protocol_name == "CoAP"

    def test_not_running_initially(self, adapter: CoAPAdapter):
        """До запуска свойство is_running=False."""
        assert adapter.is_running is False

    def test_path_helper_strips_slashes(self):
        """Метод _path() корректно разбивает пути по слэшам."""
        assert CoAPAdapter._path(
            "/ingest"
        ) == ["ingest"]
        assert CoAPAdapter._path(
            "/devices/register"
        ) == ["devices", "register"]
        assert CoAPAdapter._path(
            "health"
        ) == ["health"]
        assert CoAPAdapter._path(
            "/a/b/c/"
        ) == ["a", "b", "c"]

    def test_path_helper_empty_string(self):
        """Метод _path() на пустую строку возвращает пустой список."""
        assert CoAPAdapter._path("") == []
        assert CoAPAdapter._path("/") == []


@pytest.mark.unit
class TestCoAPAdapterLifecycle:
    """Тесты запуска и остановки адаптера."""

    @pytest.mark.asyncio
    async def test_start_sets_running(self, adapter: CoAPAdapter):
        """При запуске свойство is_running=True."""
        mock_context = AsyncMock()

        with patch(
            "aiocoap.Context.create_server_context",
            return_value=mock_context,
        ):
            await adapter.start()

        assert adapter.is_running is True

    @pytest.mark.asyncio
    async def test_stop_clears_running(self, adapter: CoAPAdapter):
        """При остановке свойство is_running=False."""
        mock_context = AsyncMock()

        with patch(
            "aiocoap.Context.create_server_context",
            return_value=mock_context,
        ):
            await adapter.start()
            await adapter.stop()

        assert adapter.is_running is False

    @pytest.mark.asyncio
    async def test_stop_calls_context_shutdown(self, adapter: CoAPAdapter):
        """При остановке останавливается и контекст."""
        mock_context = AsyncMock()

        with patch(
            "aiocoap.Context.create_server_context",
            return_value=mock_context,
        ):
            await adapter.start()
            await adapter.stop()

        mock_context.shutdown.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stop_without_start_does_not_raise(
        self, adapter: CoAPAdapter
    ):
        """Остановка без запуска не поднимает исключение."""
        await adapter.stop()

    @pytest.mark.asyncio
    async def test_start_passes_bind_tuple_to_context(
        self, adapter: CoAPAdapter
    ):
        """При инициализации контекста он получает bind с хостом и портом."""
        mock_context = AsyncMock()

        with patch(
            "aiocoap.Context.create_server_context",
            return_value=mock_context,
        ) as mock_create:
            await adapter.start()

        _, kwargs = mock_create.call_args
        bind = kwargs.get("bind") or mock_create.call_args.args[1]
        assert isinstance(bind, tuple)
        assert len(bind) == 2

    @pytest.mark.asyncio
    async def test_context_is_none_after_stop(
        self, adapter: CoAPAdapter
    ):
        """После остановки контекст уничтожен."""
        mock_context = AsyncMock()

        with patch(
            "aiocoap.Context.create_server_context",
            return_value=mock_context,
        ):
            await adapter.start()
            await adapter.stop()

        assert adapter._context is None


@pytest.mark.unit
class TestIngestResource:
    """Тесты CoAP-ресурса приёма телеметрии."""

    @pytest.mark.asyncio
    async def test_valid_telemetry_returns_changed(
        self, adapter: CoAPAdapter
    ):
        """На корректное сообщение телеметрии возвращается CHANGED."""
        resource = _IngestResource(adapter)

        request = _coap_request(
            _json_payload({"device_id": "dev-1", "payload": {"temp": 22.5}})
        )
        response = await resource.render_post(request)

        assert response.code == aiocoap.CHANGED

    @pytest.mark.asyncio
    async def test_valid_telemetry_response_is_json(
        self, adapter: CoAPAdapter
    ):
        """Ответ в формате JSON с status=accepted и message_id."""
        resource = _IngestResource(adapter)

        request = _coap_request(
            _json_payload({"device_id": "dev-1", "payload": {"temp": 22.5}})
        )
        response = await resource.render_post(request)

        body = _parse_response(response)
        assert body["status"] == "changed"
        assert "message_id" in body

    @pytest.mark.asyncio
    async def test_valid_telemetry_publishes_to_bus(self):
        """Корректное сообщение попадает на шину."""
        mock_bus = AsyncMock()
        adapter = make_adapter(mock_bus)
        resource = _IngestResource(adapter)

        request = _coap_request(
            _json_payload({"device_id": "dev-42", "payload": {"v": 1}})
        )
        await resource.render_post(request)

        mock_bus.publish.assert_awaited_once()
        topic, msg = mock_bus.publish.call_args.args
        assert topic == "telemetry.dev-42"
        assert msg.device_id == "dev-42"
        assert msg.message_type == MessageType.TELEMETRY

    @pytest.mark.asyncio
    async def test_telemetry_message_protocol_set(self):
        """В сообщение добавляется информация о протоколе."""
        mock_bus = AsyncMock()
        adapter = make_adapter(mock_bus)
        resource = _IngestResource(adapter)

        request = _coap_request(
            _json_payload({"device_id": "dev-1"})
        )
        await resource.render_post(request)

        _, msg = mock_bus.publish.call_args.args
        assert msg.protocol == "coap"

    @pytest.mark.asyncio
    async def test_missing_device_id_returns_bad_request(
        self, adapter: CoAPAdapter
    ):
        """Сообщение без device_id возвращает ошибку."""
        resource = _IngestResource(adapter)

        request = _coap_request(_json_payload({"payload": {"temp": 10}}))
        response = await resource.render_post(request)

        assert response.code == aiocoap.BAD_REQUEST
        body = _parse_response(response)
        assert body['status'] == 'error'

    @pytest.mark.asyncio
    async def test_empty_device_id_returns_bad_request(
        self, adapter: CoAPAdapter
    ):
        """Сообщение с пустым device_id возвращает ошибку."""
        resource = _IngestResource(adapter)

        request = _coap_request(_json_payload({"device_id": ""}))
        response = await resource.render_post(request)

        assert response.code == aiocoap.BAD_REQUEST

    @pytest.mark.asyncio
    async def test_invalid_json_returns_bad_request(
        self, adapter: CoAPAdapter
    ):
        """Некорректный формат вернет ошибку."""
        resource = _IngestResource(adapter)

        request = _coap_request(b"not a json{{{")
        response = await resource.render_post(request)

        assert response.code == aiocoap.BAD_REQUEST
        body = _parse_response(response)
        assert body.get('status', '') == 'error'

    @pytest.mark.asyncio
    async def test_non_utf8_payload_returns_bad_request(
        self, adapter: CoAPAdapter
    ):
        """Некорректные символы в нагрузке вернут ошибку."""
        resource = _IngestResource(adapter)

        request = _coap_request(b"\xff\xfe invalid bytes")
        response = await resource.render_post(request)

        assert response.code == aiocoap.BAD_REQUEST

    @pytest.mark.asyncio
    async def test_publish_error_returns_internal_server_error(self):
        """Ошибки на шине оглашаются INTERNAL_SERVER_ERROR."""
        mock_bus = AsyncMock()
        mock_bus.publish.side_effect = RuntimeError("bus is down")
        adapter = make_adapter(mock_bus)
        resource = _IngestResource(adapter)

        request = _coap_request(_json_payload({"device_id": "dev-1"}))
        response = await resource.render_post(request)

        assert response.code == aiocoap.INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_response_content_format_is_json(
        self, adapter: CoAPAdapter
    ):
        """Формат ответа - JSON."""
        resource = _IngestResource(adapter)

        request = _coap_request(_json_payload({"device_id": "dev-1"}))
        response = await resource.render_post(request)

        assert response.opt.content_format == ContentFormat.JSON

    @pytest.mark.asyncio
    async def test_payload_without_nested_payload_key(
        self, registry: DeviceRegistry
    ):
        """Если в теле нет ключа 'payload', весь body становится payload."""
        mock_bus = AsyncMock()
        adapter = make_adapter(mock_bus)
        resource = _IngestResource(adapter)

        body = {"device_id": "dev-flat", "temperature": 36.6}
        request = _coap_request(_json_payload(body))
        response = await resource.render_post(request)

        assert response.code == aiocoap.CHANGED
        _, msg = mock_bus.publish.call_args.args
        assert msg.payload == {'temperature': 36.6}


@pytest.mark.unit
class TestRegisterResource:
    """Тесты CoAP-ресурса регистрации устройств."""

    @pytest.mark.asyncio
    async def test_valid_register_returns_created(
        self, adapter: CoAPAdapter
    ):
        """На корректное сообщение регистрации вернется CREATED."""
        resource = _RegisterResource(adapter)

        request = _coap_request(
            _json_payload({"device_id": "dev-new", "name": "Sensor A"})
        )
        response = await resource.render_post(request)

        assert response.code == aiocoap.CREATED

    @pytest.mark.asyncio
    async def test_valid_register_response_body(
        self, adapter: CoAPAdapter
    ):
        """На корректное сообщение регистрации вернется status=registered."""
        resource = _RegisterResource(adapter)

        request = _coap_request(_json_payload({"device_id": "dev-new"}))
        response = await resource.render_post(request)

        body = _parse_response(response)
        assert body["status"] == "registered"

    @pytest.mark.asyncio
    async def test_valid_register_publishes_to_bus(self):
        """Корректное сообщение регистрации попадает на шину."""
        mock_bus = AsyncMock()
        adapter = make_adapter(mock_bus)
        resource = _RegisterResource(adapter)

        request = _coap_request(_json_payload({"device_id": "dev-55"}))
        await resource.render_post(request)

        mock_bus.publish.assert_awaited_once()
        topic, msg = mock_bus.publish.call_args.args
        assert topic == "device.register.dev-55"
        assert msg.message_type == MessageType.REGISTRATION
        assert msg.device_id == "dev-55"

    @pytest.mark.asyncio
    async def test_register_message_topic_matches_device(self):
        """Топик сообщения регистрации device.register.{device_id}."""
        mock_bus = AsyncMock()
        adapter = make_adapter(mock_bus)
        resource = _RegisterResource(adapter)

        request = _coap_request(_json_payload({"device_id": "dev-topic"}))
        await resource.render_post(request)

        _, msg = mock_bus.publish.call_args.args
        assert msg.message_topic == "device.register.dev-topic"

    @pytest.mark.asyncio
    async def test_register_message_protocol_set(self):
        """В корректное сообщение задается имя протокоал."""
        mock_bus = AsyncMock()
        adapter = make_adapter(mock_bus)
        resource = _RegisterResource(adapter)

        request = _coap_request(_json_payload({"device_id": "dev-proto"}))
        await resource.render_post(request)

        _, msg = mock_bus.publish.call_args.args
        assert msg.protocol == "coap"

    @pytest.mark.asyncio
    async def test_register_payload_contains_full_body(self):
        """Тело запроса сохраняется."""
        mock_bus = AsyncMock()
        adapter = make_adapter(mock_bus)
        resource = _RegisterResource(adapter)

        body = {
            "device_id": "dev-full",
            "name": "Temp Sensor",
            "location": "room-1"
        }
        request = _coap_request(_json_payload(body))
        await resource.render_post(request)

        _, msg = mock_bus.publish.call_args.args
        assert msg.payload == body

    @pytest.mark.asyncio
    async def test_invalid_json_returns_bad_request(
        self, adapter: CoAPAdapter
    ):
        """На некорректный формат возвращается BAD_REQUEST."""
        resource = _RegisterResource(adapter)

        request = _coap_request(b"[broken json")
        response = await resource.render_post(request)

        assert response.code == aiocoap.BAD_REQUEST

    @pytest.mark.asyncio
    async def test_publish_error_returns_internal_server_error(self):
        """На ошибки шины вернется INTERNAL_SERVER_ERROR."""
        mock_bus = AsyncMock()
        mock_bus.publish.side_effect = RuntimeError("bus offline")
        adapter = make_adapter(mock_bus)
        resource = _RegisterResource(adapter)

        request = _coap_request(_json_payload({"device_id": "dev-err"}))
        response = await resource.render_post(request)

        assert response.code == aiocoap.INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_response_content_format_is_json(
        self, adapter: CoAPAdapter
    ):
        """Формат ответа - JSON."""
        resource = _RegisterResource(adapter)

        request = _coap_request(_json_payload({"device_id": "dev-cf"}))
        response = await resource.render_post(request)

        assert response.opt.content_format == ContentFormat.JSON


@pytest.mark.unit
class TestHealthResource:
    """Тесты CoAP-ресурса health-check."""

    @pytest.mark.asyncio
    async def test_health_returns_content_code(
        self, adapter: CoAPAdapter
    ):
        """На проверку состояния вернется CONTENT."""
        resource = _HealthResource(adapter)

        response = await resource.render_get(_coap_request())

        assert response.code == aiocoap.CONTENT

    @pytest.mark.asyncio
    async def test_health_response_is_valid_json(
        self, adapter: CoAPAdapter
    ):
        """Проверка состояния возвращает JSON."""
        resource = _HealthResource(adapter)

        response = await resource.render_get(_coap_request())

        body = _parse_response(response)
        assert isinstance(body, dict)

    @pytest.mark.asyncio
    async def test_health_contains_protocol_field(
        self, adapter: CoAPAdapter
    ):
        """Проверка состояния содержит информацию о протоколе."""
        resource = _HealthResource(adapter)

        response = await resource.render_get(_coap_request())

        body = _parse_response(response)
        assert body.get("protocol") == "CoAP"

    @pytest.mark.asyncio
    async def test_health_running_false_before_start(
        self, adapter: CoAPAdapter
    ):
        """
        При проверке состояния до старта running=False.

        (Но ответ будет.)
        """
        resource = _HealthResource(adapter)

        response = await resource.render_get(_coap_request())

        body = _parse_response(response)
        assert body.get("running") is False

    @pytest.mark.asyncio
    async def test_health_running_true_after_start(
        self, adapter: CoAPAdapter
    ):
        """После старта running=True."""
        mock_context = AsyncMock()
        with patch(
            "aiocoap.Context.create_server_context",
            return_value=mock_context,
        ):
            await adapter.start()

        resource = _HealthResource(adapter)
        response = await resource.render_get(_coap_request())
        body = _parse_response(response)

        assert body.get("running") is True

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_health_content_format_is_json(
        self, adapter: CoAPAdapter
    ):
        """Формат ответа - JSON."""
        resource = _HealthResource(adapter)
        response = await resource.render_get(_coap_request())

        assert response.opt.content_format == ContentFormat.JSON


@pytest.mark.unit
class TestAdapterWithoutBus:
    """Публикация без шины должна вернуть INTERNAL_SERVER_ERROR."""

    @pytest.mark.asyncio
    async def test_ingest_without_bus_returns_error(self):
        """Без шины для телеметрии будет INTERNAL_SERVER_ERROR."""
        adapter = CoAPAdapter()  # шина НЕ подключена
        res = _IngestResource(adapter)

        request = _coap_request(_json_payload({"device_id": "dev-no-bus"}))
        response = await res.render_post(request)

        assert response.code == aiocoap.INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_register_without_bus_returns_error(self):
        """Без шины для регистрации будет INTERNAL_SERVER_ERROR."""
        adapter = CoAPAdapter()
        res = _RegisterResource(adapter)

        request = _coap_request(_json_payload({"device_id": "dev-no-bus"}))
        response = await res.render_post(request)

        assert response.code == aiocoap.INTERNAL_SERVER_ERROR
