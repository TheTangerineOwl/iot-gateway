"""Юнит-тесты для CoAPAdapter."""
import aiocoap
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from models.message import Message, MessageType
from models.device import ProtocolType
from protocols.adapters.coap_adapter import (
    CoAPAdapter,
    _IngestResource,
    _RegisterResource,
    _HealthResource,
)
from tests.conftest import DEVICE_DEF_ID
from tests.unit.protocols.conftest import json_payload, parse_response
from tests.unit.protocols.adapters.conftest import coap_request


@pytest.mark.unit
class TestCoAPAdapterProperties:
    """Базовые свойства адаптера."""

    def test_protocol_name(self, coap_adapter: CoAPAdapter):
        """Возвращается строка 'CoAP'."""
        assert coap_adapter.protocol_name == ProtocolType.COAP

    def test_protocol_type(self, coap_adapter: CoAPAdapter):
        """protocol_type соответствует ProtocolType.COAP."""
        assert coap_adapter.protocol_type == ProtocolType.COAP

    def test_not_running_initially(self, coap_adapter: CoAPAdapter):
        """До запуска is_running == False."""
        assert coap_adapter.is_running is False

    def test_context_is_none_initially(self, coap_adapter: CoAPAdapter):
        """До запуска внутренний контекст не создан."""
        assert coap_adapter._context is None

    def test_url_ingest_not_empty(self, coap_adapter: CoAPAdapter):
        """url_ingest содержит непустую строку."""
        assert (
            coap_adapter.url_ingest
            and isinstance(coap_adapter.url_ingest, str)
        )

    def test_url_register_not_empty(self, coap_adapter: CoAPAdapter):
        """url_register содержит непустую строку."""
        assert (
            coap_adapter.url_register
            and isinstance(coap_adapter.url_register, str)
        )

    def test_url_health_not_empty(self, coap_adapter: CoAPAdapter):
        """url_health содержит непустую строку."""
        assert (
            coap_adapter.url_health
            and isinstance(coap_adapter.url_health, str)
        )

    class TestPathHelper:
        """Вспомогательный метод _path()."""

        def test_leading_slash(self):
            """Убирает ведущий слэш."""
            assert CoAPAdapter._path("/ingest") == ["ingest"]

        def test_nested_path(self):
            """Разбивает вложенный путь."""
            assert CoAPAdapter._path("/devices/register") == [
                "devices", "register"
            ]

        def test_no_slash(self):
            """Путь без слэша."""
            assert CoAPAdapter._path("health") == ["health"]

        def test_trailing_slash(self):
            """Убирает trailing-слэш."""
            assert CoAPAdapter._path("/a/b/c/") == ["a", "b", "c"]

        def test_empty_string(self):
            """Пустая строка — пустой список."""
            assert CoAPAdapter._path("") == []

        def test_only_slash(self):
            """Единственный слэш — пустой список."""
            assert CoAPAdapter._path("/") == []


@pytest.mark.unit
class TestCoAPAdapterLifecycle:
    """Запуск и остановка адаптера."""

    @pytest.mark.asyncio
    async def test_start_sets_running(self, coap_adapter: CoAPAdapter):
        """После start() is_running == True."""
        with patch(
            "aiocoap.Context.create_server_context",
            return_value=AsyncMock(),
        ):
            await coap_adapter.start()

        assert coap_adapter.is_running is True

    @pytest.mark.asyncio
    async def test_start_stores_context(self, coap_adapter: CoAPAdapter):
        """После start() _context не None."""
        mock_ctx = AsyncMock()
        with patch(
            "aiocoap.Context.create_server_context",
            return_value=mock_ctx,
        ):
            await coap_adapter.start()

        assert coap_adapter._context is mock_ctx

    @pytest.mark.asyncio
    async def test_start_passes_bind_tuple(self, coap_adapter: CoAPAdapter):
        """create_server_context получает bind=(host, port)."""
        with patch(
            "aiocoap.Context.create_server_context",
            return_value=AsyncMock(),
        ) as mock_create:
            await coap_adapter.start()

        call_kwargs = mock_create.call_args[1]
        bind = call_kwargs.get("bind") or mock_create.call_args[0][1]
        assert isinstance(bind, tuple)
        assert len(bind) == 2
        assert isinstance(bind[1], int)   # порт — число

    @pytest.mark.asyncio
    async def test_stop_clears_running(self, coap_adapter: CoAPAdapter):
        """После stop() is_running == False."""
        with patch(
            "aiocoap.Context.create_server_context",
            return_value=AsyncMock(),
        ):
            await coap_adapter.start()
            await coap_adapter.stop()

        assert coap_adapter.is_running is False

    @pytest.mark.asyncio
    async def test_stop_calls_context_shutdown(
        self,
        coap_adapter: CoAPAdapter
    ):
        """stop() вызывает shutdown на контексте aiocoap."""
        mock_ctx = AsyncMock()
        with patch(
            "aiocoap.Context.create_server_context",
            return_value=mock_ctx,
        ):
            await coap_adapter.start()
            await coap_adapter.stop()

        mock_ctx.shutdown.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_context_is_none_after_stop(self, coap_adapter: CoAPAdapter):
        """После stop() _context == None."""
        with patch(
            "aiocoap.Context.create_server_context",
            return_value=AsyncMock(),
        ):
            await coap_adapter.start()
            await coap_adapter.stop()

        assert coap_adapter._context is None

    @pytest.mark.asyncio
    async def test_stop_without_start_does_not_raise(
        self, coap_adapter: CoAPAdapter
    ):
        """stop() без предшествующего start() не бросает исключения."""
        await coap_adapter.stop()   # должно пройти молча

    @pytest.mark.asyncio
    async def test_double_start_does_not_raise(
        self,
        coap_adapter: CoAPAdapter
    ):
        """Повторный start() не бросает исключения."""
        with patch(
            "aiocoap.Context.create_server_context",
            return_value=AsyncMock(),
        ):
            await coap_adapter.start()
            await coap_adapter.start()

        assert coap_adapter.is_running is True


@pytest.mark.unit
class TestIngestResource:
    """CoAP-ресурс приёма телеметрии (_IngestResource)."""

    class TestSuccess:
        """Успешная обработка запроса телеметрии."""

        @pytest.mark.asyncio
        async def test_returns_changed(self, coap_ingest: _IngestResource):
            """Корректный запрос вернет CHANGED."""
            req = coap_request(
                json_payload({"device_id": DEVICE_DEF_ID, "payload": {"t": 1}})
            )
            resp = await coap_ingest.render_post(req)
            assert resp.code == aiocoap.CHANGED

        @pytest.mark.asyncio
        async def test_response_body_has_status_changed(
            self, coap_ingest: _IngestResource
        ):
            """Тело ответа содержит status='changed'."""
            req = coap_request(
                json_payload({"device_id": DEVICE_DEF_ID, "payload": {"t": 1}})
            )
            resp = await coap_ingest.render_post(req)
            assert parse_response(resp.payload)["status"] == "changed"

        @pytest.mark.asyncio
        async def test_response_body_has_message_id(
            self, coap_ingest: _IngestResource
        ):
            """Тело ответа содержит message_id."""
            req = coap_request(
                json_payload({"device_id": DEVICE_DEF_ID})
            )
            resp = await coap_ingest.render_post(req)
            assert "message_id" in parse_response(resp.payload)

        @pytest.mark.asyncio
        async def test_publishes_to_bus(self, mock_adapter: CoAPAdapter):
            """Корректная телеметрия публикуется на шину."""
            ingest = _IngestResource(mock_adapter)
            req = coap_request(
                json_payload({"device_id": "dev-42", "payload": {"v": 99}})
            )
            await ingest.render_post(req)

            assert mock_adapter._bus is not None
            assert isinstance(mock_adapter._bus.publish, AsyncMock)
            mock_adapter._bus.publish.assert_awaited_once()

        @pytest.mark.asyncio
        async def test_publish_topic(self, mock_adapter: CoAPAdapter):
            """Топик публикации строится как 'telemetry.<device_id>'."""
            ingest = _IngestResource(mock_adapter)
            req = coap_request(
                json_payload({"device_id": "dev-42", "payload": {}})
            )
            await ingest.render_post(req)

            assert mock_adapter._bus is not None
            assert isinstance(mock_adapter._bus.publish, AsyncMock)
            topic, _ = mock_adapter._bus.publish.call_args.args
            assert topic == "telemetry.dev-42"

        @pytest.mark.asyncio
        async def test_published_message_type(self, mock_adapter: CoAPAdapter):
            """Опубликованное сообщение имеет тип TELEMETRY."""
            ingest = _IngestResource(mock_adapter)
            req = coap_request(
                json_payload({"device_id": "dev-42"})
            )
            await ingest.render_post(req)

            assert mock_adapter._bus is not None
            assert isinstance(mock_adapter._bus.publish, AsyncMock)
            _, msg = mock_adapter._bus.publish.call_args.args
            assert msg.message_type == MessageType.TELEMETRY

        @pytest.mark.asyncio
        async def test_published_message_device_id(
            self, mock_adapter: CoAPAdapter
        ):
            """device_id в опубликованном сообщении совпадает с входящим."""
            ingest = _IngestResource(mock_adapter)
            req = coap_request(
                json_payload({"device_id": "dev-42"})
            )
            await ingest.render_post(req)

            assert mock_adapter._bus is not None
            assert isinstance(mock_adapter._bus.publish, AsyncMock)
            _, msg = mock_adapter._bus.publish.call_args.args
            assert msg.device_id == "dev-42"

        @pytest.mark.asyncio
        async def test_published_message_protocol(
            self, mock_adapter: CoAPAdapter
        ):
            """Протокол в сообщении — COAP."""
            ingest = _IngestResource(mock_adapter)
            req = coap_request(
                json_payload({"device_id": "dev-42"})
            )
            await ingest.render_post(req)

            assert mock_adapter._bus is not None
            assert isinstance(mock_adapter._bus.publish, AsyncMock)
            _, msg = mock_adapter._bus.publish.call_args.args
            assert msg.protocol == ProtocolType.COAP

        @pytest.mark.asyncio
        async def test_subscribes_to_rejected_topic(
            self, mock_adapter: CoAPAdapter
        ):
            """Перед публикацией создаётся подписка на rejected.telemetry.*."""
            ingest = _IngestResource(mock_adapter)
            req = coap_request(
                json_payload({"device_id": "dev-42"})
            )
            await ingest.render_post(req)

            assert mock_adapter._bus is not None
            assert isinstance(mock_adapter._bus.subscribe, MagicMock)
            subscribe_calls = mock_adapter._bus.subscribe.call_args_list
            topics = [c.args[0] for c in subscribe_calls]
            assert any("rejected.telemetry.dev-42" in t for t in topics)

        @pytest.mark.asyncio
        async def test_unsubscribes_after_success(
            self, mock_adapter: CoAPAdapter
        ):
            """После обработки подписка снимается."""
            ingest = _IngestResource(mock_adapter)
            req = coap_request(
                json_payload({"device_id": "dev-42"})
            )
            await ingest.render_post(req)

            assert mock_adapter._bus is not None
            assert isinstance(mock_adapter._bus.unsubscribe, MagicMock)
            mock_adapter._bus.unsubscribe.assert_called()

    class TestRejection:
        """Сообщение отклонено пайплайном."""

        @pytest.mark.asyncio
        async def test_rejected_returns_forbidden(
            self, mock_adapter: CoAPAdapter
        ):
            """Если пайплайн отклонил — возвращается FORBIDDEN."""
            ingest = _IngestResource(mock_adapter)

            async def _publish_and_reject(topic, message):
                fut = mock_adapter._pending.get(message.message_id)
                if fut:
                    rejected = Message(
                        message_id=message.message_id,
                        device_id=message.device_id,
                        metadata={
                            "reject_reason": "bad_schema",
                            "reject_stage": "validation",
                        },
                    )
                    fut.set_result(rejected)

            assert mock_adapter._bus is not None
            assert isinstance(mock_adapter._bus, MagicMock)
            mock_adapter._bus.publish = AsyncMock(
                side_effect=_publish_and_reject
            )
            mock_adapter._timeout_reject = 2.0

            req = coap_request(
                json_payload({"device_id": "dev-42"})
            )
            resp = await ingest.render_post(req)
            assert resp.code == aiocoap.FORBIDDEN

        @pytest.mark.asyncio
        async def test_rejected_response_has_reason(
            self, mock_adapter: CoAPAdapter
        ):
            """Тело FORBIDDEN-ответа содержит reason из метаданных."""
            ingest = _IngestResource(mock_adapter)

            async def _publish_and_reject(topic, message):
                fut = mock_adapter._pending.get(message.message_id)
                if fut:
                    rejected = Message(
                        message_id=message.message_id,
                        device_id=message.device_id,
                        metadata={
                            "reject_reason": "bad_schema",
                            "reject_stage": "validation",
                        },
                    )
                    fut.set_result(rejected)

            assert mock_adapter._bus is not None
            assert isinstance(mock_adapter._bus, MagicMock)
            mock_adapter._bus.publish = AsyncMock(
                side_effect=_publish_and_reject
            )
            mock_adapter._timeout_reject = 2.0

            req = coap_request(
                json_payload({"device_id": "dev-42"})
            )
            resp = await ingest.render_post(req)
            body = parse_response(resp.payload)
            assert body.get("reason") == "bad_schema"
            assert body.get("stage") == "validation"
            assert body.get("status") == "rejected"

        @pytest.mark.asyncio
        async def test_timeout_yields_changed(self, mock_adapter: CoAPAdapter):
            """Если пайплайн не ответил вовремя — всё равно CHANGED."""
            mock_adapter._timeout_reject = 0.01   # очень короткий таймаут
            ingest = _IngestResource(mock_adapter)

            req = coap_request(
                json_payload({"device_id": "dev-42"})
            )
            resp = await ingest.render_post(req)
            assert resp.code == aiocoap.CHANGED

        @pytest.mark.asyncio
        async def test_pending_cleared_after_timeout(
            self, mock_adapter: CoAPAdapter
        ):
            """После таймаута future удаляется из _pending."""
            mock_adapter._timeout_reject = 0.01
            ingest = _IngestResource(mock_adapter)

            req = coap_request(
                json_payload({"device_id": "dev-42"})
            )
            await ingest.render_post(req)

            assert len(mock_adapter._pending) == 0

    class TestBadRequest:
        """Некорректные входящие данные."""

        @pytest.mark.asyncio
        async def test_missing_device_id_returns_bad_request(
            self, coap_ingest: _IngestResource
        ):
            """Без device_id вернет BAD_REQUEST."""
            req = coap_request(json_payload({"payload": {"t": 1}}))
            resp = await coap_ingest.render_post(req)
            assert resp.code == aiocoap.BAD_REQUEST

        @pytest.mark.asyncio
        async def test_missing_device_id_error_body(
            self, coap_ingest: _IngestResource
        ):
            """Тело BAD_REQUEST содержит error_code."""
            req = coap_request(json_payload({"payload": {"t": 1}}))
            resp = await coap_ingest.render_post(req)
            body = parse_response(resp.payload)
            assert body["status"] == "error"
            assert "error_code" in body

        @pytest.mark.asyncio
        async def test_invalid_json_returns_bad_request(
            self, coap_ingest: _IngestResource
        ):
            """Невалидный JSON вернет BAD_REQUEST."""
            req = coap_request(b"not-json")
            resp = await coap_ingest.render_post(req)
            assert resp.code == aiocoap.BAD_REQUEST

        @pytest.mark.asyncio
        async def test_invalid_json_error_body(
            self, coap_ingest: _IngestResource
        ):
            """Тело ответа на невалидный JSON — JSON с ошибкой."""
            req = coap_request(b"{broken")
            resp = await coap_ingest.render_post(req)
            body = parse_response(resp.payload)
            assert body["status"] == "error"
            assert "INVALID_JSON" in body.get("error_code", "")

        @pytest.mark.asyncio
        async def test_empty_payload_returns_bad_request(
            self, coap_ingest: _IngestResource
        ):
            """Пустой payload вернет BAD_REQUEST (нет device_id)."""
            req = coap_request(b"{}")
            resp = await coap_ingest.render_post(req)
            assert resp.code == aiocoap.BAD_REQUEST

        @pytest.mark.asyncio
        async def test_non_utf8_payload_returns_bad_request(
            self, coap_ingest: _IngestResource
        ):
            """Двоичный мусор (не UTF-8) вернет BAD_REQUEST."""
            req = coap_request(b"\xff\xfe")
            resp = await coap_ingest.render_post(req)
            assert resp.code == aiocoap.BAD_REQUEST

    class TestInternalError:
        """Внутренние ошибки при публикации."""

        @pytest.mark.asyncio
        async def test_bus_not_connected_returns_internal_error(
            self,
            config
        ):
            """Шина не подключена вернет INTERNAL_SERVER_ERROR."""
            coap_adapter = CoAPAdapter(config)   # без set_gateway_context
            ingest = _IngestResource(coap_adapter)
            req = coap_request(
                json_payload({"device_id": "dev-1"})
            )
            resp = await ingest.render_post(req)
            assert resp.code == aiocoap.INTERNAL_SERVER_ERROR

        @pytest.mark.asyncio
        async def test_publish_raises_runtime_returns_internal_error(
            self, mock_adapter: CoAPAdapter
        ):
            """Ошибка при publish вернет INTERNAL_SERVER_ERROR."""
            assert mock_adapter._bus is not None
            assert isinstance(mock_adapter._bus, MagicMock)
            mock_adapter._bus.publish = AsyncMock(
                side_effect=RuntimeError("boom")
            )
            ingest = _IngestResource(mock_adapter)
            req = coap_request(
                json_payload({"device_id": "dev-1"})
            )
            resp = await ingest.render_post(req)
            assert resp.code == aiocoap.INTERNAL_SERVER_ERROR

        @pytest.mark.asyncio
        async def test_pending_cleared_on_publish_error(
            self, mock_adapter: CoAPAdapter
        ):
            """При ошибке публикации future удаляется из _pending."""
            assert mock_adapter._bus is not None
            assert isinstance(mock_adapter._bus, MagicMock)
            mock_adapter._bus.publish = AsyncMock(
                side_effect=RuntimeError("boom")
            )
            ingest = _IngestResource(mock_adapter)
            req = coap_request(
                json_payload({"device_id": "dev-1"})
            )
            await ingest.render_post(req)

            assert len(mock_adapter._pending) == 0


@pytest.mark.unit
class TestRegisterResource:
    """CoAP-ресурс регистрации устройства (_RegisterResource)."""

    class TestSuccess:
        """Успешная регистрация."""

        @pytest.mark.asyncio
        async def test_returns_created(self, coap_register: _RegisterResource):
            """Корректный запрос регистрации вернет CREATED."""
            req = coap_request(
                json_payload({"device_id": DEVICE_DEF_ID, "name": "Sensor A"})
            )
            resp = await coap_register.render_post(req)
            assert resp.code == aiocoap.CREATED

        @pytest.mark.asyncio
        async def test_response_body_status_registered(
            self, coap_register: _RegisterResource
        ):
            """Тело ответа содержит status='registered'."""
            req = coap_request(
                json_payload({"device_id": DEVICE_DEF_ID})
            )
            resp = await coap_register.render_post(req)
            assert parse_response(resp.payload)["status"] == "registered"

        @pytest.mark.asyncio
        async def test_response_body_has_message_id(
            self, coap_register: _RegisterResource
        ):
            """Тело ответа содержит message_id."""
            req = coap_request(
                json_payload({"device_id": DEVICE_DEF_ID})
            )
            resp = await coap_register.render_post(req)
            assert "message_id" in parse_response(resp.payload)

        @pytest.mark.asyncio
        async def test_publishes_to_bus(self, mock_adapter: CoAPAdapter):
            """Запрос регистрации публикуется на шину."""
            register = _RegisterResource(mock_adapter)
            req = coap_request(
                json_payload({"device_id": DEVICE_DEF_ID})
            )
            await register.render_post(req)

            assert mock_adapter._bus is not None
            assert isinstance(mock_adapter._bus.publish, AsyncMock)
            mock_adapter._bus.publish.assert_awaited_once()

        @pytest.mark.asyncio
        async def test_publish_topic(self, mock_adapter: CoAPAdapter):
            """Топик публикации — 'device.register.<device_id>'."""
            register = _RegisterResource(mock_adapter)
            req = coap_request(
                json_payload({"device_id": "dev-99"})
            )
            await register.render_post(req)

            assert mock_adapter._bus is not None
            assert isinstance(mock_adapter._bus.publish, AsyncMock)
            topic, _ = mock_adapter._bus.publish.call_args.args
            assert topic == "device.register.dev-99"

        @pytest.mark.asyncio
        async def test_published_message_type(self, mock_adapter: CoAPAdapter):
            """Опубликованное сообщение имеет тип REGISTRATION."""
            register = _RegisterResource(mock_adapter)
            req = coap_request(
                json_payload({"device_id": DEVICE_DEF_ID})
            )
            await register.render_post(req)

            assert mock_adapter._bus is not None
            assert isinstance(mock_adapter._bus.publish, AsyncMock)
            _, msg = mock_adapter._bus.publish.call_args.args
            assert msg.message_type == MessageType.REGISTRATION

        @pytest.mark.asyncio
        async def test_published_message_protocol(
            self, mock_adapter: CoAPAdapter
        ):
            """Протокол в сообщении — COAP."""
            register = _RegisterResource(mock_adapter)
            req = coap_request(
                json_payload({"device_id": DEVICE_DEF_ID})
            )
            await register.render_post(req)

            assert mock_adapter._bus is not None
            assert isinstance(mock_adapter._bus.publish, AsyncMock)
            _, msg = mock_adapter._bus.publish.call_args.args
            assert msg.protocol == ProtocolType.COAP

        @pytest.mark.asyncio
        async def test_message_topic_set_correctly(
            self, mock_adapter: CoAPAdapter
        ):
            """message_topic в сообщении совпадает с топиком публикации."""
            register = _RegisterResource(mock_adapter)
            req = coap_request(
                json_payload({"device_id": "dev-99"})
            )
            await register.render_post(req)

            assert mock_adapter._bus is not None
            assert isinstance(mock_adapter._bus.publish, AsyncMock)
            _, msg = mock_adapter._bus.publish.call_args.args
            assert msg.message_topic == "device.register.dev-99"

    class TestBadRequest:
        """Некорректные входящие данные при регистрации."""

        @pytest.mark.asyncio
        async def test_invalid_json_returns_bad_request(
            self, coap_register: _RegisterResource
        ):
            """Невалидный JSON вернет BAD_REQUEST."""
            req = coap_request(b"not-json")
            resp = await coap_register.render_post(req)
            assert resp.code == aiocoap.BAD_REQUEST

        @pytest.mark.asyncio
        async def test_invalid_json_error_body(
            self, coap_register: _RegisterResource
        ):
            """Тело ответа на невалидный JSON содержит ошибку."""
            req = coap_request(b"{bad}")
            resp = await coap_register.render_post(req)
            body = parse_response(resp.payload)
            assert body["status"] == "error"
            assert "INVALID_JSON" in body.get("error_code", "")

        @pytest.mark.asyncio
        async def test_non_utf8_returns_bad_request(
            self, coap_register: _RegisterResource
        ):
            """Двоичный мусор вернет BAD_REQUEST."""
            req = coap_request(b"\xff\xfe")
            resp = await coap_register.render_post(req)
            assert resp.code == aiocoap.BAD_REQUEST

    class TestInternalError:
        """Внутренние ошибки при регистрации."""

        @pytest.mark.asyncio
        async def test_publish_raises_returns_internal_error(
            self, mock_adapter: CoAPAdapter
        ):
            """Ошибка при publish вернет INTERNAL_SERVER_ERROR."""
            assert mock_adapter._bus is not None
            assert isinstance(mock_adapter._bus, MagicMock)
            mock_adapter._bus.publish = AsyncMock(
                side_effect=RuntimeError("bus down")
            )
            register = _RegisterResource(mock_adapter)
            req = coap_request(
                json_payload({"device_id": DEVICE_DEF_ID})
            )
            resp = await register.render_post(req)
            assert resp.code == aiocoap.INTERNAL_SERVER_ERROR

        @pytest.mark.asyncio
        async def test_internal_error_body(self, mock_adapter: CoAPAdapter):
            """Тело INTERNAL_SERVER_ERROR содержит status='error'."""
            assert mock_adapter._bus is not None
            assert isinstance(mock_adapter._bus, MagicMock)
            mock_adapter._bus.publish = AsyncMock(
                side_effect=RuntimeError("bus down")
            )
            register = _RegisterResource(mock_adapter)
            req = coap_request(
                json_payload({"device_id": DEVICE_DEF_ID})
            )
            resp = await register.render_post(req)
            body = parse_response(resp.payload)
            assert body["status"] == "error"


@pytest.mark.unit
class TestHealthResource:
    """CoAP-ресурс состояния (_HealthResource)."""

    @pytest.mark.asyncio
    async def test_returns_content(self, coap_health: _HealthResource):
        """GET /health вернет CONTENT."""
        req = aiocoap.Message(code=aiocoap.GET)
        resp = await coap_health.render_get(req)
        assert resp.code == aiocoap.CONTENT

    @pytest.mark.asyncio
    async def test_response_is_valid_json(self, coap_health: _HealthResource):
        """Ответ парсится как JSON без ошибок."""
        req = aiocoap.Message(code=aiocoap.GET)
        resp = await coap_health.render_get(req)
        body = parse_response(resp.payload)
        assert isinstance(body, dict)

    @pytest.mark.asyncio
    async def test_response_has_protocol(self, coap_health: _HealthResource):
        """В ответе присутствует поле 'protocol'."""
        req = aiocoap.Message(code=aiocoap.GET)
        resp = await coap_health.render_get(req)
        assert "protocol" in parse_response(resp.payload)

    @pytest.mark.asyncio
    async def test_response_has_running(self, coap_health: _HealthResource):
        """В ответе присутствует поле 'running'."""
        req = aiocoap.Message(code=aiocoap.GET)
        resp = await coap_health.render_get(req)
        assert "running" in parse_response(resp.payload)

    @pytest.mark.asyncio
    async def test_running_false_when_not_started(
        self, coap_health: _HealthResource
    ):
        """До запуска адаптера running == False."""
        req = aiocoap.Message(code=aiocoap.GET)
        resp = await coap_health.render_get(req)
        assert parse_response(resp.payload)["running"] is False

    @pytest.mark.asyncio
    async def test_protocol_value(self, coap_health: _HealthResource):
        """Поле protocol соответствует имени протокола адаптера."""
        req = aiocoap.Message(code=aiocoap.GET)
        resp = await coap_health.render_get(req)
        assert parse_response(resp.payload)["protocol"] == "CoAP"

    @pytest.mark.asyncio
    async def test_running_true_when_started(
        self, mock_adapter: CoAPAdapter
    ):
        """После старта адаптера running == True в health-ответе."""
        with patch(
            "aiocoap.Context.create_server_context",
            return_value=AsyncMock(),
        ):
            await mock_adapter.start()

        health_res = _HealthResource(mock_adapter)
        req = aiocoap.Message(code=aiocoap.GET)
        resp = await health_res.render_get(req)
        assert parse_response(resp.payload)["running"] is True

        await mock_adapter.stop()
