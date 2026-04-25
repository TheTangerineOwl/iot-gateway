"""
Сервис для получения устройств и телеметрии со шлюза.

Работает через HTTP/TCP к запущенному шлюзу.
"""
import logging
import aiohttp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.dependencies.config import Settings
from web.backend.services.gateway import _http_health


logger = logging.getLogger(__name__)


async def fetch_devices(settings: Settings) -> list[dict] | None:
    """Получить список устройств из management-адаптера."""
    url = f"{settings.gateway_management_url.rstrip('/')}/management/devices/"
    ok, body = await _http_health(url, settings.check_timeout)
    if not ok or not body:
        return None
    return body.get("devices", [])


async def fetch_device(settings: Settings, device_id: str) -> dict | None:
    """Получить данные одного устройства из management-адаптера."""
    url = (
        f"{settings.gateway_management_url.rstrip('/')}"
        f"/management/devices/{device_id}"
    )
    ok, body = await _http_health(url, settings.check_timeout)
    if not ok or not body:
        return None
    return body


async def send_device_command(
    settings: Settings,
    device_id: str,
    command: str,
    params: dict | None = None,
    timeout: float = 10.0,
) -> tuple[int, dict]:
    """
    Проксировать команду на management-адаптер шлюза.

    Returns:
        (http_status_code, response_body)
    """
    url = (
        f"{settings.gateway_management_url.rstrip('/')}"
        f"/management/devices/{device_id}/command"
    )
    payload = {"command": command, "params": params or {}, "timeout": timeout}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout + 2),
            ) as resp:
                body = await resp.json(content_type=None)
                return resp.status, body
    except Exception as exc:
        logger.warning("Не удалось отправить команду на шлюз: %s", exc)
        return 502, {"error": str(exc)}


async def fetch_last_telemetry(
    db: AsyncSession,
    device_id: str,
    limit: int = 20,
) -> list[dict]:
    """Получить последние N записей телеметрии для устройства из БД."""
    result = await db.execute(
        text(
            "SELECT device_id, payload, timestamp, message_id, protocol "
            "FROM telemetry "
            "WHERE device_id = :device_id "
            "ORDER BY timestamp DESC "
            "LIMIT :limit"
        ),
        {"device_id": device_id, "limit": limit},
    )
    rows = result.mappings().all()
    return [dict(row) for row in rows]
