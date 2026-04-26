"""
Management-адаптер шлюза.

Запускает минимальный HTTP-сервер для внутреннего мониторинга.
Не принимает телеметрию, не участвует в шине сообщений.

Эндпоинты:
    GET /management/status  — текущий статус шлюза
    GET /management/config  — конфигурация шлюза
"""
import logging
from http import HTTPStatus
from typing import TYPE_CHECKING
from aiohttp import web

from config.config import YAMLConfigLoader
from models.device import ProtocolType
from models.message import Message, MessageType
from config.topics import TopicKey
from protocols.adapters.base import ProtocolAdapter

if TYPE_CHECKING:
    from core.gateway import Gateway

logger = logging.getLogger(__name__)


class ManagementAdapter(ProtocolAdapter):
    """Адаптер внутреннего HTTP-управления шлюзом."""

    def __init__(self, config: YAMLConfigLoader, gateway: "Gateway") -> None:
        """
        Адаптер внутреннего HTTP-управления шлюзом.

        Args:
            config:  общий конфиг шлюза (YAMLConfigLoader).
            gateway: ссылка на экземпляр Gateway — для вызова
                     status и configuration.
        """
        super().__init__(config)
        self._gateway = gateway

        adapter_cfg = self._config.get_adapter_config("management")
        self._host: str = adapter_cfg.get("host", "0.0.0.0")
        self._port: int = adapter_cfg.get("port", 8001)
        self._url_root: str = adapter_cfg.get("url_root", "/management")

        endpoints = adapter_cfg.get("endpoints", {})
        self._url_status: str = self._url_root + endpoints.get(
            "status",
            "/status"
        )
        self._url_config: str = self._url_root + endpoints.get(
            "config",
            "/config"
        )

        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None

    @property
    def protocol_type(self) -> ProtocolType:
        """Тип протокола."""
        return ProtocolType.HTTP_GATEWAY

    async def start(self) -> None:
        """Запустить management HTTP-сервер."""
        self._app = web.Application()
        self._app.router.add_get(self._url_status, self._handle_status)
        self._app.router.add_get(self._url_config, self._handle_config)
        self._app.router.add_post(
            self._url_root + "/devices/{device_id}/command",
            self._handle_command,
        )
        self._app.router.add_get(
            self._url_root + "/devices/",
            self._handle_list_devices,
        )
        self._app.router.add_get(
            self._url_root + "/devices/{device_id}",
            self._handle_get_device,
        )
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        site = web.TCPSite(self._runner, self._host, self._port)
        await site.start()

        self._running = True
        logger.info(
            "Management adapter listening on %s:%d  (http://%s:%d%s)",
            self._host, self._port,
            self._host, self._port,
            self._url_root,
        )

    async def stop(self) -> None:
        """Остановить management HTTP-сервер."""
        self._running = False
        if self._runner:
            await self._runner.cleanup()
        logger.info("Management adapter stopped")

    async def _handle_status(self, request: web.Request) -> web.Response:
        """GET /management/status — возвращает gateway.status."""
        gw_status = await self._gateway.status
        return web.json_response(
            gw_status,
            status=HTTPStatus.OK,
        )

    async def _handle_config(self, request: web.Request) -> web.Response:
        """GET /management/config — возвращает gateway.configuration."""
        gw_config = self._gateway.configuration
        return web.json_response(
            gw_config,
            status=HTTPStatus.OK,
        )

    async def _handle_command(self, request: web.Request) -> web.Response:
        """Обработать отправку команды для устройства."""
        device_id = request.match_info["device_id"]

        try:
            body: dict = await request.json()
        except Exception:
            return web.json_response(
                {"error": "invalid JSON"}, status=HTTPStatus.BAD_REQUEST
            )

        command = body.get("command")
        if not command:
            return web.json_response(
                {"error": "field 'command' is required"},
                status=HTTPStatus.BAD_REQUEST,
            )

        params: dict = body.get("params", {})
        timeout = float(body.get("timeout", 10.0))

        message = Message(
            message_type=MessageType.COMMAND,
            device_id=device_id,
            payload={"command": command, "params": params},
            message_topic=self._gateway.bus.topics.get(
                TopicKey.DEVICES_COMMAND, device_id=device_id
            ),
        )
        command_str = command + ''.join(
            [f' {k} {v}' for k, v in params.items()]
        )

        response_msg = await self._gateway._command_tracker.send_and_wait(
            message=message,
            bus_publish_coro=self._gateway.bus.publish(
                message.message_topic, message
            ),
            timeout=timeout,
        )

        if response_msg is None:
            return web.json_response(
                {
                    "status": "timeout",
                    "device_id": device_id,
                    "command": command_str,
                    "message_id": message.message_id,
                },
                status=HTTPStatus.GATEWAY_TIMEOUT,
            )

        return web.json_response(
            {
                "status": "ok",
                "device_id": device_id,
                "command": command_str,
                "message_id": message.message_id,
                "response": response_msg.payload,
            },
            status=HTTPStatus.OK,
        )

    async def send_command(self, device_id, command, params=None):
        """
        Заглушка для метода из ProtocolAdapter.

        ManagementAdapter отвечает за связь между веб-приложением
        и шлюзом, поэтому не связан с оконечным устройством.
        Команду отправлять некуда.
        """
        logger.warning(
            "ManagementAdapter does not support send_command "
            "(device_id=%s, command=%s)", device_id, command
        )
        return False

    async def _handle_list_devices(self, request: web.Request) -> web.Response:
        """GET /management/devices/ — список всех устройств из реестра."""
        registry = self._gateway.registry
        devices = [d.to_dict() for d in registry._devices.values()]
        return web.json_response({"devices": devices, "total": len(devices)})

    async def _handle_get_device(self, request: web.Request) -> web.Response:
        """GET /management/devices/{device_id} — один девайс."""
        device_id = request.match_info["device_id"]
        registry = self._gateway.registry
        device = registry.get(device_id)
        if device is None:
            return web.json_response(
                {"error": f"device '{device_id}' not found"},
                status=HTTPStatus.NOT_FOUND,
            )
        return web.json_response(device.to_dict())
