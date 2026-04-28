"""
Сервис для получения устройств и телеметрии со шлюза.

Работает через HTTP/TCP к запущенному шлюзу.
"""
import logging
from aiohttp import ClientPayloadError
from http import HTTPStatus
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.dependencies.config import Settings
from web.backend.services.management import fetch_from_gateway, send_post
from web.backend.schemas.devices import (
    Device, DeviceList,
    CommandRequest, CommandResponse,
    Telemetry, TelemetryList
)


logger = logging.getLogger(__name__)


SELECT_DEVICES_SQL = """
SELECT device_id, payload, timestamp, message_id
 FROM telemetry
 WHERE device_id = :device_id
 ORDER BY timestamp DESC
 LIMIT :limit
"""


async def fetch_devices(settings: Settings) -> DeviceList:
    """Получить список устройств из management-адаптера."""
    url = f"{settings.gateway_management_url.rstrip('/')}/management/devices/"
    body = await fetch_from_gateway(url, settings.check_timeout)
    devices = body.get("devices")
    if not devices:
        raise KeyError("'devices' не в теле ответа")
    total = len(devices)
    return DeviceList(devices=devices, total=total)


async def fetch_device(settings: Settings, device_id: str) -> Device:
    """Получить данные одного устройства из management-адаптера."""
    url = (
        f"{settings.gateway_management_url.rstrip('/')}"
        f"/management/devices/{device_id}"
    )
    body = await fetch_from_gateway(url, settings.check_timeout)
    return Device(**body)


async def send_device_command(
    settings: Settings,
    device_id: str,
    request: CommandRequest
) -> CommandResponse:
    """
    Проксировать команду на management-адаптер шлюза.

    Returns:
        (http_status_code, response_body)
    """
    url = (
        f"{settings.gateway_management_url.rstrip('/')}"
        f"/management/devices/{device_id}/command"
    )
    payload = request.model_dump()
    status, body = await send_post(url, payload, request.timeout + 2)
    if status < 300 and body:
        response = CommandResponse(**body)
    elif status == HTTPStatus.GATEWAY_TIMEOUT:
        raise TimeoutError('Таймаут')
    elif status == HTTPStatus.BAD_GATEWAY or not body:
        raise ClientPayloadError('Не удалось отправить команду')
    return response


async def fetch_last_telemetry(
    db: AsyncSession,
    device_id: str,
    limit: int = 20,
) -> TelemetryList:
    """Получить последние N записей телеметрии для устройства из БД."""
    if limit <= 0:
        raise ValueError('limit должен быть положительным')
    result = await db.execute(
        text(SELECT_DEVICES_SQL),
        {"device_id": device_id, "limit": limit},
    )
    rows = result.mappings().all()
    telemetry = [Telemetry(**row) for row in rows][:limit]
    return TelemetryList(telemetry=telemetry, total=len(telemetry))
