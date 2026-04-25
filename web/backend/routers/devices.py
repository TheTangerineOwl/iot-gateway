"""
Роутер устройств.

Эндпоинты:
  GET  /web/api/devices/
  — список всех устройств из БД
  GET  /web/api/devices/{device_id}
  — детали устройства + последние телеметрии
  POST  /web/api/devices/{device_id}/command
  — отправить команду через HTTP-адаптер шлюза
"""
import logging
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.models.user import User
from web.backend.dependencies.auth import get_current_user
from web.backend.dependencies.config import Settings, get_settings
from web.backend.dependencies.database import get_session
from web.backend.schemas.devices import CommandRequest
from web.backend.services.devices import (
    fetch_devices,
    fetch_device,
    send_device_command,
    fetch_last_telemetry
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["devices"])


@router.get(
    "/",
    summary="Список всех устройств",
    responses={
        200: {"description": "Список устройств"},
        401: {"description": "Не авторизован"},
        502: {"description": "Шлюз недоступен"},
    },
)
async def list_devices(
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Возвращает список всех зарегистрированных устройств из реестра шлюза."""
    devices = await fetch_devices(settings)
    if devices is None:
        return JSONResponse(
            status_code=502,
            content={"detail": "шлюз недоступен"},
        )
    return JSONResponse(
        status_code=200,
        content={"devices": devices, "total": len(devices)},
    )


@router.get(
    "/{device_id}",
    summary="Детали устройства",
    responses={
        200: {"description": "Детали устройства и последняя телеметрия"},
        401: {"description": "Не авторизован"},
        404: {"description": "Устройство не найдено"},
        502: {"description": "Шлюз недоступен"},
    },
)
async def get_device(
    device_id: str,
    limit: int = Query(
        default=20,
        gt=0,
        # le=200,
        description="Количество записей телеметрии"
    ),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Возвращает детали устройства и последние N записей телеметрии."""
    device = await fetch_device(settings, device_id)

    if device is None:
        # Шлюз вернул 404 или недоступен — различаем по тому, что вернулось
        # fetch_device возвращает None как при 404, так и при сетевой ошибке.
        # При необходимости можно расширить fetch_device для передачи статуса.
        return JSONResponse(
            status_code=404,
            content={
                "detail":
                    f"устройство '{device_id}' не найдено или шлюз недоступен"
            },
        )

    telemetry = await fetch_last_telemetry(db, device_id, limit=limit)

    return JSONResponse(
        status_code=200,
        content={
            "device": device,
            "telemetry": telemetry,
        },
    )


@router.post(
    "/{device_id}/command",
    summary="Отправить команду устройству",
    responses={
        200: {"description": "Команда отправлена, получен ответ"},
        400: {"description": "Некорректное тело запроса"},
        401: {"description": "Не авторизован"},
        502: {"description": "Шлюз недоступен"},
        504: {"description": "Устройство не ответило за отведённое время"},
    },
)
async def send_command(
    device_id: str,
    body: CommandRequest,
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """
    Проксирует команду на management-адаптер шлюза:
    POST {gateway_management_url}/management/devices/{device_id}/command
    """
    status_code, response_body = await send_device_command(
        settings=settings,
        device_id=device_id,
        command=body.command,
        params=body.params,
    )

    return JSONResponse(status_code=status_code, content=response_body)
