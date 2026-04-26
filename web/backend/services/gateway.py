"""
Сервис для получения статуса и конфигурации шлюза.

Работает через HTTP/TCP к запущенному шлюзу.
"""
import logging

from web.backend.dependencies.config import Settings
from web.backend.services.management import fetch_from_gateway
from web.backend.schemas.gateway.status import GatewayStatus
from web.backend.schemas.gateway.config import GatewayConfig


logger = logging.getLogger(__name__)


async def fetch_gateway_status(settings: Settings) -> GatewayStatus:
    """Получить статус шлюза с менеджмент-адаптера."""
    url = f"{settings.gateway_management_url.rstrip('/')}/management/status"
    body = await fetch_from_gateway(url, settings.check_timeout)
    return GatewayStatus(**body)


async def fetch_gateway_config(settings: Settings) -> GatewayConfig:
    """Получить конфигурацию шлюза через management-адаптер."""
    url = f"{settings.gateway_management_url.rstrip('/')}/management/config"
    body = await fetch_from_gateway(url, settings.check_timeout)
    return GatewayConfig(**body)
