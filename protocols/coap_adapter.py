"""Адаптер для протокола CoAP."""
import asyncio
import aiocoap
import aiocoap.resource as resource
from aiocoap.numbers.contentformat import ContentFormat
import json
import logging
from typenv import Env
from typing import Any
from models.message import Message, MessageType
from protocols.adapter import ProtocolAdapter


env = Env(upper=True)
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
                payload=json.dumps({'error': 'Invalid JSON'}).encode(),
                content_format=ContentFormat.JSON,
            )

        device_id: str = body.get('device_id', '')
        if not device_id:
            return aiocoap.Message(
                code=aiocoap.BAD_REQUEST,
                payload=json.dumps({'error': 'device_id required'}).encode(),
                content_format=ContentFormat.JSON,
            )

        message = Message(
            message_type=MessageType.TELEMETRY,
            device_id=device_id,
            protocol=self._adapter.protocol_name.lower(),
            message_topic=self._adapter.url_ingest,
            payload=body.get('payload', body),
        )

        try:
            await self._adapter._publish_message(
                f'telemetry.{device_id}', message
            )
        except RuntimeError as exc:
            logger.error('CoAP ingest: publish error — %s', exc)
            return aiocoap.Message(
                code=aiocoap.INTERNAL_SERVER_ERROR,
                payload=json.dumps({'error': str(exc)}).encode(),
                content_format=ContentFormat.JSON,
            )

        logger.log(5, 'CoAP adapter got telemetry: %s', message.to_dict())

        return aiocoap.Message(
            code=aiocoap.CHANGED,
            payload=json.dumps(
                {'status': 'accepted', 'message_id': message.message_id}
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
                payload=json.dumps({'error': 'Invalid JSON'}).encode(),
                content_format=ContentFormat.JSON,
            )

        message = Message(
            message_type=MessageType.REGISTRATION,
            device_id=body.get('device_id', ""),
            protocol=self._adapter.protocol_name.lower(),
            message_topic=self._adapter.url_register,
            payload=body,
        )
        message.message_topic = f'device.register.{message.device_id}'

        try:
            await self._adapter._publish_message(
                f'device.register.{message.device_id}', message
            )
        except RuntimeError as exc:
            logger.error('CoAP register: publish error — %s', exc)
            return aiocoap.Message(
                code=aiocoap.INTERNAL_SERVER_ERROR,
                payload=json.dumps({'error': str(exc)}).encode(),
                content_format=ContentFormat.JSON,
            )

        logger.log(5, 'CoAP adapter got register: %s', message.to_dict())

        return aiocoap.Message(
            code=aiocoap.CREATED,
            payload=json.dumps({'status': 'registered'}).encode(),
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

    def __init__(self) -> None:
        """Инициализировать CoAP-адаптер, прочитав настройки из env."""
        super().__init__()
        self._host: str = env.str('COAP_HOST', default='0.0.0.0')
        self._port: int = env.int('COAP_PORT', default=5683)

        root_url: str = env.str('COAP_URL_ROOT', default='api/v1/coap')

        self._url_ingest: str = root_url + env.str(
            'COAP_URL_TELEMETRY', default='/ingest'
        )
        self._url_register: str = root_url + env.str(
            'COAP_URL_REGISTER', default='/devices/register'
        )
        self._url_health: str = root_url + env.str(
            'COAP_URL_HEALTH', default='/health'
        )

        self._context: aiocoap.Context | None = None
        self._serve_task: asyncio.Task | None = None

    @property
    def protocol_name(self) -> str:
        """Имя протокола у адаптера."""
        return 'CoAP'

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

        self._running = True
        logger.info(
            'CoAP adapter listening on coap://%s:%d',
            self._host,
            self._port,
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
