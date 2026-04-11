"""
Адаптер для протокола HTTP.

Эндпоинты:

    POST /api/v1/ingest приём телеметрии
    POST /api/v1/devices/register регистрация устройства
    GET /api/v1/health чек
"""
from aiohttp import web
from http import HTTPStatus
import json
import logging
from typenv import Env
from typing import Any
from models.message import MessageType
from protocols.adapter import ProtocolAdapter
from .message_builder import MessageBuilder


env = Env(upper=True)
logger = logging.getLogger(__name__)


class HTTPAdapter(ProtocolAdapter):
    """Адаптер для протокола HTTP."""

    def __init__(self) -> None:
        """Адаптер для протокола HTTP."""
        super().__init__()
        self._host = env.str('HTTP_HOST', default='0.0.0.0')
        self._port = env.int('HTTP_PORT', default=8081)
        self._root_url = env.str('HTTP_URL_ROOT', default='/api/v1')
        self._wh_telemetry = self._root_url + env.str(
            'HTTP_URL_TELEMETRY',
            default='/ingest'
        )
        self._url_register = self._root_url + env.str(
            'HTTP_URL_REGISTER',
            default='/devices/register'
        )
        self._url_health = self._root_url + env.str(
            'HTTP_URL_HEALTH',
            default='/health'
        )

        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None

    @property
    def protocol_name(self) -> str:
        """Имя протокола у адаптера."""
        return "HTTP"

    def _build_meta(self, request: web.Request):
        return {
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote,
            'headers': {
                k.lower(): v
                for k, v in request.headers.items()
                if k.lower() in (
                    'content-type', 'x-device-token',
                    'user-agent', 'x-correlation-id'
                )
            }
        }

    async def start(self) -> None:
        """Запустить HTTP-сервера."""
        self._app = web.Application()
        self._app.router.add_post(
            self._wh_telemetry,
            self._handle_ingest
        )
        self._app.router.add_post(
            self._url_register,
            self._handle_register
        )
        self._app.router.add_get(
            self._url_health,
            self._handle_health
        )

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        site = web.TCPSite(self._runner, self._host, self._port)
        await site.start()

        self._running = True
        logger.info(
            "HTTP adapter listening on %s:%d  (http://%s:%d%s)",
            self._host, self._port,
            self._host, self._port,
            self._root_url
        )

    async def stop(self) -> None:
        """Остановить HTTP-сервер."""
        self._running = False
        if self._runner:
            await self._runner.cleanup()
        logger.info("HTTP adapter stopped")

    async def _handle_ingest(self, request) -> Any:
        """Приём телеметрии."""
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response(
                MessageBuilder.err_inval_json(),
                status=HTTPStatus.BAD_REQUEST
            )

        proto_meta = self._build_meta(request)

        message = MessageBuilder.normalize(
            body,
            protocol_name=self.protocol_name,
            topic=self._wh_telemetry,
            proto_meta=proto_meta
        )

        if not message.device_id:
            return web.json_response(
                MessageBuilder.err_miss_dev_id(),
                status=HTTPStatus.BAD_REQUEST
            )

        await self._publish_message(f"telemetry.{message.device_id}", message)

        logger.log(5, 'HTTP adapter got telemetry: %s', message.to_dict())

        return web.json_response(
            MessageBuilder.build_msg(message, 'accepted'),
            status=HTTPStatus.ACCEPTED
        )

    async def _handle_register(self, request) -> Any:
        """Прием сообщения о регистрации."""
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response(
                MessageBuilder.err_inval_json(),
                status=HTTPStatus.BAD_REQUEST
            )

        proto_meta = self._build_meta(request)

        message = MessageBuilder.normalize(
            body,
            protocol_name=self.protocol_name,
            topic=self._url_register,
            proto_meta=proto_meta,
            message_type=MessageType.REGISTRATION
        )

        if not message.device_id:
            return web.json_response(
                MessageBuilder.err_miss_dev_id(),
                status=HTTPStatus.BAD_REQUEST
            )

        message.message_topic = f"device.register.{message.device_id}"
        await self._publish_message(
            f"device.register.{message.device_id}",
            message
        )

        logger.log(5, 'HTTP adapter got register: %s', message.to_dict())

        return web.json_response(
            MessageBuilder.build_msg(message, 'registered'),
            status=HTTPStatus.CREATED
        )

    async def _handle_health(self, request) -> Any:
        """Обработчик проверки здоровья адаптера."""
        health = await self._health_check()

        json = await request.json()
        if json:
            id = str(json.get('device_id', ''))
            if len(id) > 0:
                logger.log(5, 'Health check from device %s', id)

        logger.log(5, 'HTTP got health check')

        return web.json_response(health)
