"""Менеджер контекста для http-симулятора."""
import aiohttp
import logging
from typenv import Env
from typing import Any
from simulator.base.client_base import GatewayClient
from simulator.device import SimulatedDevice


env = Env(upper=True)
logger = logging.getLogger(__name__)


class HTTPGatewayClient(GatewayClient):
    """Менеджер контекста для http-симулятора."""

    def __init__(self, timeout: float = 5.0) -> None:
        """Создать сессию http-клиента для симулятора."""
        self._host = env.str('SIM_HTTP_HOST', default='127.0.0.1')
        self._port = env.int('SIM_HTTP_PORT', default=8081)
        self._root_url = env.str('HTTP_URL_ROOT', default='/api/v1') + '/'
        self._wh_telemetry = env.str(
            'HTTP_URL_TELEMETRY',
            default='/ingest'
        ).lstrip('/')
        self._url_register = env.str(
            'HTTP_URL_REGISTER',
            default='/devices/register'
        ).lstrip('/')
        self._url_health = env.str(
            'HTTP_URL_HEALTH',
            default='/health'
        ).lstrip('/')
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "HTTPGatewayClient":
        """Начать сессию http-клиента."""
        base = f'http://{self._host}:{self._port}{self._root_url}'
        self._session = aiohttp.ClientSession(
            base_url=base,
            timeout=self._timeout
        )
        logger.info(f'Started session with base_url {base}')
        return self

    async def __aexit__(self, *_: object) -> None:
        """Завершить сессию http-клиента."""
        if self._session:
            await self._session.close()

    async def register(self, device: SimulatedDevice) -> tuple[int, Any]:
        """Зарегистрировать девайс."""
        assert self._session, "Use as async context manager"
        async with self._session.post(
            self._url_register,
            json=device.build_register()
        ) as resp:
            try:
                data = await resp.json(content_type=None)
            except Exception:
                data = {"raw": await resp.text()}
            return resp.status, data

    async def send(self, body: dict[str, Any]) -> tuple[int, dict]:
        """Отправить одно сообщение. Вернуть (status_code, response_body)."""
        assert self._session, "Use as async context manager"
        async with self._session.post(self._wh_telemetry, json=body) as resp:
            try:
                data = await resp.json(content_type=None)
            except Exception:
                data = {"raw": await resp.text()}
            return resp.status, data
