"""
Адаптер для протокола HTTP.

Эндпоинты:

    POST /api/v1/ingest приём телеметрии
    POST /api/v1/devices/register регистрация устройства
    GET /api/v1/health чек
"""
import asyncio
from aiohttp import web, ClientSession, ClientTimeout, ClientError
from http import HTTPStatus
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


class HTTPAdapter(ProtocolAdapter):
    """Адаптер для протокола HTTP."""

    def __init__(self, config: YAMLConfigLoader) -> None:
        """Адаптер для протокола HTTP."""
        super().__init__(config)
        self._adapter_config = self._config.get_adapter_config(
            self.protocol_name.lower()
        )
        self._host: str = self._adapter_config.get('host', '0.0.0.0')
        self._port: int = self._adapter_config.get('port', 8081)

        self._root_url: str = self._adapter_config.get('url_root', '/api/v1')
        self._endpoints: dict[str, str] = self._adapter_config.get(
            'endpoints',
            {}
        )
        self._wh_telemetry: str = (
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
        self._url_commands: str = (
            self._root_url
            + self._endpoints.get('commands', '/devices/{device_id}/commands')
        )

        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._timeout: float = self._adapter_config.get('timeout_reject', 0.5)

        self._command_queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}
        self._http_session: ClientSession | None = None
        self._cmd_timeout: float = float(
            self._adapter_config.get('command_timeout', 5.0)
        )

    @property
    def protocol_type(self) -> ProtocolType:
        """Тип протокола."""
        return ProtocolType.HTTP

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
            },

            'callback_url': request.remote
        }

    async def start(self) -> None:
        """Запустить HTTP-сервера."""
        self._http_session = ClientSession()

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
        self._app.router.add_get(
            self._url_commands,
            self._handle_poll_commands,
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
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()
            self._http_session = None
        if self._runner:
            await self._runner.cleanup()
        logger.info("HTTP adapter stopped")

    async def _handle_ingest(self, request) -> Any:
        """Приём телеметрии."""
        try:
            body: dict[str, Any] = await request.json()
        except json.JSONDecodeError:
            return web.json_response(
                MessageBuilder.err_inval_json(),
                status=HTTPStatus.BAD_REQUEST
            )

        proto_meta = self._build_meta(request)

        device_id = body.get('device_id', None)

        if not device_id:
            return web.json_response(
                MessageBuilder.err_miss_dev_id(),
                status=HTTPStatus.BAD_REQUEST
            )

        message = MessageBuilder.normalize(
            body,
            protocol=self.protocol_type,
            topic=self.get_topic(
                TopicKey.DEVICES_TELEMETRY,
                device_id=device_id
            ),
            proto_meta=proto_meta
        )

        fut = self._register_pending(message)

        assert self._bus is not None
        sub = self._bus.subscribe(
            self.get_topic(
                TopicKey.REJECTED_TELEMETRY,
                device_id=device_id
            ),
            self._handle_rejected_base
        )

        await self._publish_message(
            message.message_topic,
            message
        )

        logger.log(5, 'HTTP adapter got telemetry: %s', message.to_dict())

        try:
            rejected_msg: Message = await asyncio.wait_for(
                asyncio.shield(fut),
                timeout=self._timeout
            )
            reason = rejected_msg.metadata.get('reject_reason', 'filtered')
            stage = rejected_msg.metadata.get('reject_stage', 'unknown')
            self._bus.unsubscribe(sub)
            return web.json_response(
                MessageBuilder.build_msg(
                    rejected_msg,
                    status='rejected',
                    reason=reason,
                    stage=stage
                ),
                status=HTTPStatus.UNPROCESSABLE_ENTITY
            )
        except asyncio.TimeoutError:
            pass
        finally:
            self._pending.pop(message.message_id, None)

        self._bus.unsubscribe(sub)
        return web.json_response(
            MessageBuilder.build_msg(message, 'accepted'),
            status=HTTPStatus.ACCEPTED
        )

    async def _handle_register(self, request) -> Any:
        """Прием сообщения о регистрации."""
        try:
            body: dict[str, Any] = await request.json()
        except json.JSONDecodeError:
            return web.json_response(
                MessageBuilder.err_inval_json(),
                status=HTTPStatus.BAD_REQUEST
            )

        proto_meta = self._build_meta(request)

        device_id = body.get('device_id', None)

        if not device_id:
            return web.json_response(
                MessageBuilder.err_miss_dev_id(),
                status=HTTPStatus.BAD_REQUEST
            )

        message = MessageBuilder.normalize(
            body,
            protocol=self.protocol_type,
            topic=self.get_topic(
                TopicKey.DEVICES_REGISTER,
                device_id=device_id
            ),
            proto_meta=proto_meta,
            message_type=MessageType.REGISTRATION
        )

        await self._publish_message(
            message.message_topic,
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

        logger.log(5, 'HTTP got health check')

        return web.json_response(health)

    async def send_command(
        self,
        device_id: str,
        command: str,
        params: dict[str, Any] | None = None,
    ) -> bool:
        """
        Отправить команду HTTP-устройству.

        Стратегия (выбирается автоматически):
        1. PUSH через callback_url — если устройство зарегистрировало URL.
        2. PULL-очередь — команда помещается в очередь, устройство
        забирает её через GET /devices/{id}/commands.

        Args:
            device_id: идентификатор устройства.
            command:   имя команды.
            params:    параметры команды.

        Returns:
            True  — команда доставлена (push) или поставлена в очередь (pull).
            False — адаптер не может доставить команду.
        """
        payload: dict[str, Any] = {
            'command': command,
            'params': params or {},
        }

        # Push: callback_url
        if self._registry is not None:
            device = self._registry.get(device_id)
            callback_url: str | None = (
                device.metadata.get('callback_url') if device else None
            )
            if callback_url:
                return await self._push_command(
                    device_id,
                    callback_url,
                    payload
                )

        # Pull: internal queue
        logger.info(
            "send_command: no callback_url for device '%s', "
            "queuing command '%s' for pull",
            device_id, command,
        )
        return self._enqueue_command(device_id, payload)

    async def _push_command(
        self,
        device_id: str,
        callback_url: str,
        payload: dict[str, Any],
    ) -> bool:
        """POST команды на callback_url устройства."""
        if self._http_session is None or self._http_session.closed:
            logger.error("send_command: HTTP session is not open")
            return False

        try:
            async with self._http_session.post(
                callback_url,
                json=payload,
                timeout=ClientTimeout(total=self._cmd_timeout),
            ) as resp:
                if resp.status < 300:
                    logger.info(
                        "Command '%s' pushed to device '%s' - %s (%d)",
                        payload['command'],
                        device_id,
                        callback_url,
                        resp.status,
                    )
                    return True
                else:
                    body = await resp.text()
                    logger.warning(
                        "Command push to device '%s' failed: HTTP %d — %s",
                        device_id, resp.status, body[:200],
                    )
                    # Деградируем до очереди, чтобы команда не потерялась
                    logger.info(
                        "Falling back to pull queue for device '%s'", device_id
                    )
                    return self._enqueue_command(device_id, payload)

        except asyncio.TimeoutError:
            logger.warning(
                "Command push timeout for device '%s' (%s)",
                device_id, callback_url,
            )
            return self._enqueue_command(device_id, payload)

        except ClientError as exc:
            logger.error(
                "HTTP client error pushing command to device '%s': %s",
                device_id, exc,
            )
            return self._enqueue_command(device_id, payload)

    def _enqueue_command(
        self, device_id: str, payload: dict[str, Any]
    ) -> bool:
        """Поместить команду во внутреннюю очередь для pull-получения."""
        if device_id not in self._command_queues:
            self._command_queues[device_id] = asyncio.Queue(maxsize=100)
        queue = self._command_queues[device_id]
        try:
            queue.put_nowait(payload)
            logger.debug(
                "Command '%s' enqueued for device '%s' (queue size: %d)",
                payload['command'], device_id, queue.qsize(),
            )
            return True
        except asyncio.QueueFull:
            logger.warning(
                "Command queue full for device '%s', dropping command '%s'",
                device_id, payload['command'],
            )
            return False

    async def _handle_poll_commands(
        self,
        request: web.Request
    ) -> web.Response:
        """
        GET /api/v1/devices/{device_id}/commands.

        Устройство без callback-URL опрашивает этот эндпоинт.
        Возвращает все накопленные команды
        (до max_batch штук) и очищает очередь.
        """
        device_id: str = request.match_info['device_id']
        max_batch: int = int(request.rel_url.query.get('limit', 10))

        queue = self._command_queues.get(device_id)
        commands: list[dict[str, Any]] = []

        if queue:
            while not queue.empty() and len(commands) < max_batch:
                try:
                    commands.append(queue.get_nowait())
                except asyncio.QueueEmpty:
                    break

        logger.debug(
            "Poll commands for device '%s': returning %d command(s)",
            device_id, len(commands),
        )
        return web.json_response({'commands': commands}, status=HTTPStatus.OK)
