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
from protocols.adapters.base import ProtocolAdapter

if TYPE_CHECKING:
    from core.gateway import Gateway

logger = logging.getLogger(__name__)


class ManagementAdapter(ProtocolAdapter):
    """Адаптер внутреннего HTTP-управления шлюзом."""

    def __init__(self, config: YAMLConfigLoader, gateway: "Gateway") -> None:
        """
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
        return ProtocolType.HTTP_GATEWAY

    async def start(self) -> None:
        """Запустить management HTTP-сервер."""
        self._app = web.Application()
        self._app.router.add_get(self._url_status, self._handle_status)
        self._app.router.add_get(self._url_config, self._handle_config)

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
