"""Адаптер для протокола CoAP."""
import asyncio
import aiocoap
import aiocoap.resource as resource
from aiocoap.numbers.contentformat import ContentFormat
import json
import logging
from typing import Any
from config.config import YAMLConfigLoader
from config.topics import TopicKey
from models.message import MessageType, Message
from models.device import ProtocolType
from protocols.adapters.base import ProtocolAdapter
from protocols.message_builder import MessageBuilder


logger = logging.getLogger(__name__)


class _IngestResource(resource.Resource):
    """CoAP-ресурс: приём телеметрии."""

    def __init__(self, adapter: 'CoAPAdapter') -> None:
        super().__init__()
        self._adapter = adapter

    async def render_post(self, request: aiocoap.Message) -> aiocoap.Message:
        """Обработать POST-запрос с телеметрией."""
        try:
            body: dict[str, Any] = json.loads(request.payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning('CoAP ingest: bad payload — %s', exc)
            return aiocoap.Message(
                code=aiocoap.BAD_REQUEST,
                payload=json.dumps(
                    MessageBuilder.err_inval_json()
                ).encode(),
                content_format=ContentFormat.JSON,
            )

        device_id: str = body.get('device_id', '')
        if not device_id:
            return aiocoap.Message(
                code=aiocoap.BAD_REQUEST,
                payload=json.dumps(
                    MessageBuilder.err_miss_dev_id()
                ).encode(),
                content_format=ContentFormat.JSON,
            )
        sub = None
        try:
            message: Message | None = None
            if not self._adapter._bus:
                raise RuntimeError(
                    f'Adapter {self._adapter.protocol_name} not '
                    'connected to message bus.'
                )

            message = MessageBuilder.normalize(
                body,
                protocol=self._adapter.protocol_type,
                topic=self._adapter.get_topic(
                    TopicKey.DEVICES_TELEMETRY,
                    device_id=device_id
                ),
                message_type=MessageType.TELEMETRY,
                proto_meta=self._adapter._build_meta(request)
            )

            sub = self._adapter._bus.subscribe(
                self._adapter.get_topic(
                    TopicKey.REJECTED_TELEMETRY,
                    device_id=device_id
                ),
                self._adapter._handle_rejected_base
            )
            fut = self._adapter._register_pending(message)

            await self._adapter._publish_message(
                message.message_topic, message
            )
        except RuntimeError as exc:
            if message:
                self._adapter._pending.pop(message.message_id, None)
            logger.error('CoAP ingest: publish error — %s', exc)
            if sub and self._adapter._bus:
                self._adapter._bus.unsubscribe(sub)
            return aiocoap.Message(
                code=aiocoap.INTERNAL_SERVER_ERROR,
                payload=json.dumps(
                    MessageBuilder.err_internal(str(exc))
                ).encode(),
                content_format=ContentFormat.JSON,
            )

        logger.log(5, 'CoAP adapter got telemetry: %s', message.to_dict())

        try:
            rejected_msg: Message = await asyncio.wait_for(
                asyncio.shield(fut),
                timeout=self._adapter._timeout_reject
            )
            reason = rejected_msg.metadata.get('reject_reason', 'filtered')
            stage = rejected_msg.metadata.get('reject_stage', 'unknown')
            self._adapter._bus.unsubscribe(sub)
            return aiocoap.Message(
                code=aiocoap.FORBIDDEN,
                payload=json.dumps(
                    MessageBuilder.build_msg(
                        rejected_msg,
                        status='rejected',
                        reason=reason,
                        stage=stage
                    )
                ).encode(),
                content_format=ContentFormat.JSON
            )
        except asyncio.TimeoutError:
            pass
        finally:
            self._adapter._pending.pop(message.message_id, None)
        if sub:
            self._adapter._bus.unsubscribe(sub)
        return aiocoap.Message(
            code=aiocoap.CHANGED,
            payload=json.dumps(
                MessageBuilder.build_msg(message, 'changed')
            ).encode(),
            content_format=ContentFormat.JSON,
        )


class _RegisterResource(resource.Resource):
    """CoAP-ресурс: регистрация устройства."""

    def __init__(self, adapter: 'CoAPAdapter') -> None:
        super().__init__()
        self._adapter = adapter

    async def render_post(self, request: aiocoap.Message) -> aiocoap.Message:
        """Обработать POST-запрос регистрации устройства."""
        try:
            body: dict[str, Any] = json.loads(request.payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning('CoAP register: bad payload — %s', exc)
            return aiocoap.Message(
                code=aiocoap.BAD_REQUEST,
                payload=json.dumps(
                    MessageBuilder.err_inval_json()
                ).encode(),
                content_format=ContentFormat.JSON,
            )

        device_id = body.get('device_id', None)

        if not device_id:
            logger.error('CoAP register: device_id is required')
            return aiocoap.Message(
                code=aiocoap.BAD_REQUEST,
                payload=json.dumps(
                    MessageBuilder.err_miss_dev_id()
                ).encode(),
                content_format=ContentFormat.JSON,
            )

        message = MessageBuilder.normalize(
            body,
            protocol=self._adapter.protocol_type,
            topic=self._adapter.get_topic(
                TopicKey.DEVICES_REGISTER,
                device_id=device_id
            ),
            message_type=MessageType.REGISTRATION,
            proto_meta=self._adapter._build_meta(request)
        )

        try:
            await self._adapter._publish_message(
                message.message_topic, message
            )
        except RuntimeError as exc:
            logger.error('CoAP register: publish error — %s', exc)
            return aiocoap.Message(
                code=aiocoap.INTERNAL_SERVER_ERROR,
                payload=json.dumps(
                    MessageBuilder.err_internal(str(exc))
                ).encode(),
                content_format=ContentFormat.JSON,
            )

        logger.log(5, 'CoAP adapter got register: %s', message.to_dict())

        return aiocoap.Message(
            code=aiocoap.CREATED,
            payload=json.dumps(
                MessageBuilder.build_msg(message, status='registered')
            ).encode(),
            content_format=ContentFormat.JSON,
        )


class _HealthResource(resource.Resource):
    """CoAP-ресурс: состояние адаптера."""

    def __init__(self, adapter: 'CoAPAdapter') -> None:
        super().__init__()
        self._adapter = adapter

    async def render_get(self, request: aiocoap.Message) -> aiocoap.Message:
        """Вернуть JSON с состоянием адаптера."""
        health = await self._adapter._health_check()
        logger.log(5, 'CoAP health check')
        return aiocoap.Message(
            code=aiocoap.CONTENT,
            payload=json.dumps(health).encode(),
            content_format=ContentFormat.JSON,
        )


class CoAPAdapter(ProtocolAdapter):
    """Адаптер для протокола CoAP (UDP, порт 5683 по умолчанию).

    Поднимает aiocoap-сервер.
    """

    def __init__(self, config: YAMLConfigLoader) -> None:
        """Инициализировать CoAP-адаптер, прочитав настройки из env."""
        super().__init__(config)
        self._config = config
        self._adapter_config: dict[str, Any] = self._config.get_adapter_config(
            self.protocol_name.lower()
        )
        self._host: str = self._adapter_config.get(
            'host',
            '0.0.0.0'
        )
        self._port: int = self._adapter_config.get(
            'port',
            5683
        )

        self._root_url: str = self._adapter_config.get(
            'url_root',
            '/api/v1/coap'
        )
        self._endpoints: dict[str, str] = self._adapter_config.get(
            'endpoints',
            {}
        )
        self._url_ingest: str = (
            self._root_url
            + self._endpoints.get('telemetry', '/ingest')
        )
        self._url_register: str = (
            self._root_url
            + self._endpoints.get('register', '/devices/register')
        )
        self._url_health: str = (
            self._root_url
            + self._endpoints.get('health', '/heatlh')
        )

        self._context: aiocoap.Context | None = None
        self._serve_task: asyncio.Task | None = None

        self._timeout_reject: float = self._adapter_config.get(
            'timeout_reject',
            0.5
        )

    @property
    def protocol_type(self) -> ProtocolType:
        """Тип протокола у адаптера."""
        return ProtocolType.COAP

    @property
    def url_ingest(self) -> str:
        """URL-путь ресурса телеметрии."""
        return self._url_ingest

    @property
    def url_register(self) -> str:
        """URL-путь ресурса регистрации."""
        return self._url_register

    @property
    def url_health(self) -> str:
        """URL-путь ресурса health-check."""
        return self._url_health

    async def start(self) -> None:
        """Запустить CoAP-сервер."""
        root = resource.Site()

        # .well-known/core — стандартное обнаружение ресурсов
        root.add_resource(
            ['.well-known', 'core'],
            resource.WKCResource(root.get_resources_as_linkheader),
        )

        root.add_resource(
            self._path(self._url_ingest),
            _IngestResource(self),
        )
        root.add_resource(
            self._path(self._url_register),
            _RegisterResource(self),
        )
        root.add_resource(
            self._path(self._url_health),
            _HealthResource(self),
        )

        bind = (self._host, self._port)
        self._context = await aiocoap.Context.create_server_context(
            root, bind=bind
        )

        # assert self._bus is not None
        # self._bus.subscribe(
        #     'rejected.telemetry.*',
        #     self._handle_rejected_base
        # )

        self._running = True
        logger.info(
            'CoAP adapter listening on %s:%s  (coap://%s:%d%s)',
            self._host, self._port,
            self._host, self._port,
            self._root_url
        )

    async def stop(self) -> None:
        """Остановить CoAP-сервер."""
        self._running = False
        if self._context is not None:
            await self._context.shutdown()
            self._context = None
        logger.info('CoAP adapter stopped')

    @staticmethod
    def _path(url: str) -> list[str]:
        """Преобразовать строку URL-пути в список сегментов для aiocoap."""
        return [seg for seg in url.strip('/').split('/') if seg]

    def _build_meta(self, request: aiocoap.Message) -> dict[str, Any]:
        """Построить метаданные протокола."""
        return {
            'callback_url':
                f'coap://{request.remote.hostinfo}'
                if request.remote and request.remote.hostinfo else None
        }

    async def send_command(
        self,
        device_id: str,
        command: str,
        params: dict[str, Any] | None = None,
    ) -> bool:
        """
        Отправить CON-запрос на CoAP-устройство.

        Требует, чтобы адрес устройства (coap://host:port/command) был известен
        заранее — например, сохранён в Device.metadata['coap_address'] при
        получении первого пакета от устройства.
        """
        if self._registry is None:
            return False

        device = self._registry.get(device_id)
        if device is None:
            logger.warning(
                "send_command: device '%s' not found in registry", device_id
            )
            return False

        coap_address = device.metadata.get(
            "coap_address"
        ) if hasattr(device, "metadata") else None
        if not coap_address:
            logger.warning(
                "send_command: no coap_address for device '%s'. "
                "Store it in Device.metadata['coap_address'] on first packet.",
                device_id,
            )
            return False

        try:
            context = await aiocoap.Context.create_client_context()
            payload_bytes = json.dumps(
                {"command": command, "params": params or {}}
            ).encode()
            request = aiocoap.Message(
                code=aiocoap.POST,
                uri=f"{coap_address}/command",
                payload=payload_bytes,
            )
            response = await context.request(request).response
            logger.info(
                "CoAP command '%s' sent to device '%s', response code: %s",
                command, device_id, response.code,
            )
            await context.shutdown()
            return response.code.is_successful()
        except Exception as exc:
            logger.error(
                "send_command: CoAP error for device '%s': %s",
                device_id, exc, exc_info=True,
            )
            return False
