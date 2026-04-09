"""
Адаптер для протокола WebSocket.

Эндпоинты:

    GET  /api/v1/ws          двунаправленный WebSocket-канал
    GET  /api/v1/ws/health   HTTP-проверка состояния адаптера
    POST /api/v1/ws/register HTTP-регистрация устройства
"""
import asyncio
from aiohttp import web, WSMsgType
import json
import logging
from http import HTTPStatus
from typenv import Env
from typing import Any
from models.message import Message, MessageType
from protocols.adapter import ProtocolAdapter


env = Env(upper=True)
logger = logging.getLogger(__name__)


class WebSocketAdapter(ProtocolAdapter):
    """Адаптер для протокола WebSocket."""

    def __init__(self, heartbeat: float | None = 30.0) -> None:
        """Адаптер для протокола WebSocket."""
        super().__init__()

        self._host: str = env.str('WS_HOST', default='0.0.0.0')
        self._port: int = env.int('WS_PORT', default=8082)
        self._root_url: str = env.str('WS_URL_ROOT', default='/api/v1/ws')

        self._url_ws_telemetry: str = self._root_url + env.str(
            'WS_URL_WS', default='/ingest'
        )
        self._url_register: str = self._root_url + env.str(
            'WS_URL_REGISTER', default='/register'
        )
        self._url_health: str = self._root_url + env.str(
            'WS_URL_HEALTH', default='/health'
        )

        self._connections: dict[str, web.WebSocketResponse] = {}
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None

        self._heartbeat = heartbeat

    @property
    def protocol_name(self) -> str:
        """Имя протокола у адаптера."""
        return 'WebSocket'

    async def start(self) -> None:
        """Запустить WebSocket-сервер."""
        self._app = web.Application()

        self._app.router.add_get(
            self._url_ws_telemetry,
            self._handle_ws_ingest
        )
        self._app.router.add_post(
            self._url_register,
            self._handle_register
        )
        self._app.router.add_get(
            self._url_register,
            self._handle_ws_ingest
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
            'WebSocket adapter listening on %s:%d  (ws://%s:%d%s)',
            self._host,
            self._port,
            self._host,
            self._port,
            self._root_url,
        )

    async def stop(self) -> None:
        """Остановить WebSocket-сервер."""
        self._running = False

        for device_id, ws in list(self._connections.items()):
            try:
                await ws.close()
            except Exception as exc:
                logger.warning(
                    "Error closing WebSocket for device '%s': %s",
                    device_id,
                    exc, exc_info=True
                )
        self._connections.clear()

        if self._runner:
            await self._runner.cleanup()

        logger.info('WebSocket adapter stopped')

    async def _handle_ws_ingest(
            self, request: web.Request
    ) -> web.WebSocketResponse:
        """
        Основной WebSocket-обработчик.

        Устанавливает постоянное соединение с устройством.
        Каждое входящее JSON-сообщение маршрутизируется по полю type.
        """
        ws = web.WebSocketResponse(heartbeat=self._heartbeat)
        await ws.prepare(request)

        # device_id становится известен после первого сообщения
        device_id: str | None = None

        logger.debug(
            'WebSocket connection opened from %s',
            request.remote,
        )

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    device_id = await self._dispatch_text(
                        ws, msg.data, device_id, request.remote
                    )

                elif msg.type == WSMsgType.ERROR:
                    logger.warning(
                        "WebSocket error from device '%s': %s",
                        device_id,
                        ws.exception(),
                    )
                    break

        except asyncio.CancelledError:
            pass
        finally:
            if device_id and self._connections.get(device_id) is ws:
                del self._connections[device_id]
                logger.debug(
                    "WebSocket connection closed for device '%s'",
                    device_id,
                )

        return ws

    async def _handle_register(self, request: web.Request) -> web.Response:
        """HTTP-регистрация устройства."""
        try:
            body: dict[str, Any] = await request.json()
        except (json.JSONDecodeError, Exception):
            return web.json_response(
                {'error': 'Invalid JSON'},
                status=HTTPStatus.BAD_REQUEST,
            )

        message = Message(
            message_type=MessageType.REGISTRATION,
            device_id=body.get('device_id', ''),
            protocol=self.protocol_name.lower(),
            message_topic=self._url_register,
            payload=body,
        )
        message.message_topic = f'device.register.{message.device_id}'
        await self._publish_message(
            f'device.register.{message.device_id}', message
        )

        logger.log(5, 'WebSocket HTTP-register: %s', message.to_dict())

        return web.json_response(
            {'status': 'registered'},
            status=HTTPStatus.CREATED,
        )

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Проверка состояния адаптера."""
        health = await self._health_check()
        health['connections'] = len(self._connections)
        logger.log(5, 'WebSocket health check')
        return web.json_response(health)

    async def _dispatch_text(
        self,
        ws: web.WebSocketResponse,
        raw: str,
        device_id: str | None,
        remote: str | None,
    ) -> str | None:
        """
        Разобрать текстовое WebSocket-сообщение и направить его в шину.

        Возвращает актуальный device_id (может быть обновлён из сообщения).
        """
        try:
            body: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            await self._send_error(ws, 'Invalid JSON')
            return device_id

        msg_type = body.get('type', 'telemetry')
        incoming_id = body.get('device_id', device_id or '')

        if not incoming_id:
            await self._send_error(ws, 'device_id required')
            return device_id

        if device_id != incoming_id:
            device_id = incoming_id
            if device_id is None:  # для Mypy
                await self._send_error(ws, 'device_id required')
                return device_id
            self._connections[device_id] = ws
            logger.debug(
                "WebSocket device identified: '%s' (%s)",
                device_id,
                remote,
            )

        if msg_type == 'telemetry':
            await self._process_telemetry(ws, body, device_id)

        elif msg_type == 'heartbeat':
            await self._process_heartbeat(ws, device_id)

        elif msg_type == 'register':
            await self._process_ws_register(ws, body, device_id)

        else:
            await self._send_error(
                ws, f"Unknown message type: '{msg_type}'"
            )

        return device_id

    async def _process_telemetry(
        self,
        ws: web.WebSocketResponse,
        body: dict[str, Any],
        device_id: str,
    ) -> None:
        """Обработать телеметрию, пришедшую по WebSocket."""
        message = Message(
            message_type=MessageType.TELEMETRY,
            device_id=device_id,
            protocol=self.protocol_name.lower(),
            message_topic=f'telemetry.{device_id}',
            payload=body.get('payload', body),
        )
        await self._publish_message(f'telemetry.{device_id}', message)

        logger.log(5, 'WebSocket telemetry: %s', message.to_dict())

        await ws.send_json(
            {
                'status': 'accepted',
                'message_id': message.message_id,
            }
        )

    async def _process_heartbeat(
        self,
        ws: web.WebSocketResponse,
        device_id: str,
    ) -> None:
        """Обработать heartbeat-сообщение по WebSocket."""
        message = Message(
            message_type=MessageType.HEARTBEAT,
            device_id=device_id,
            protocol=self.protocol_name.lower(),
            message_topic=f'device.heartbeat.{device_id}',
            payload={},
        )
        await self._publish_message(
            f'device.heartbeat.{device_id}', message
        )

        logger.log(5, "WebSocket heartbeat from device '%s'", device_id)

        await ws.send_json({'status': 'ok'})

    async def _process_ws_register(
        self,
        ws: web.WebSocketResponse,
        body: dict[str, Any],
        device_id: str,
    ) -> None:
        """Обработать регистрацию устройства, пришедшую по WebSocket."""
        message = Message(
            message_type=MessageType.REGISTRATION,
            device_id=device_id,
            protocol=self.protocol_name.lower(),
            message_topic=f'device.register.{device_id}',
            payload=body.get('payload', body),
        )
        await self._publish_message(
            f'device.register.{device_id}', message
        )

        logger.log(5, 'WebSocket register: %s', message.to_dict())

        await ws.send_json({'status': 'registered'})

    async def _send_error(
        self, ws: web.WebSocketResponse, error: str
    ) -> None:
        """Отправить сообщение об ошибке клиенту."""
        try:
            await ws.send_json({'error': error})
        except Exception as exc:
            logger.warning('Failed to send error to client: %s', exc)

    async def _health_check(self) -> dict[str, Any]:
        """Расширенное состояние WebSocket-адаптера."""
        base = await super()._health_check()
        base['connections'] = len(self._connections)
        return base
