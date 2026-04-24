"""
Сервис для получения статуса и конфигурации шлюза.

Работает через HTTP/TCP к запущенному шлюзу.
"""
import logging
from typing import Optional
import aiohttp

from web.backend.dependencies.config import Settings
from web.backend.schemas.gateway.status import GatewayStatus
from web.backend.schemas.gateway.config import GatewayConfig


logger = logging.getLogger(__name__)


async def _http_health(
    url: str,
    timeout: float,
) -> tuple[bool, Optional[dict]]:
    """
    Делает GET-запрос к health-check эндпоинту шлюза.

    Returns:
        (True, request body) — если статус 200
        (False, None) — если недоступен или ошибка
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status == 200:
                    body = await resp.json(content_type=None)
                    return True, body
                return False, None
    except Exception as exc:
        logger.debug("Health-check %s недоступен: %s", url, exc)
        return False, None


async def fetch_gateway_status(settings: Settings) -> GatewayStatus | None:
    url = f"{settings.gateway_management_url.rstrip('/')}/management/status"
    ok, body = await _http_health(url, settings.check_timeout)
    if not ok or not body:
        return None
    return GatewayStatus(**body)


async def fetch_gateway_config(settings: Settings) -> GatewayConfig | None:
    """Получить конфигурацию шлюза через management-адаптер."""
    url = f"{settings.gateway_management_url.rstrip('/')}/management/config"
    ok, body = await _http_health(url, settings.check_timeout)
    if not ok or not body:
        return None
    return GatewayConfig(**body)
