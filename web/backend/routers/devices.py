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
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from web.backend.models.user import User
from web.backend.dependencies.auth import get_current_user


router = APIRouter(tags=["devices"])


@router.get(
    "/",
    summary="Список всех устройств",
    responses={
        200: {"description": "Список устройств"},
        401: {"description": "Не авторизован"},
        501: {"description": "Ещё не реализовано"},
    },
)
async def list_devices(
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Возвращает список всех зарегистрированных устройств (read-only)."""
    return JSONResponse(
        status_code=501,
        content={
            "detail": "not implemented",
            "endpoint": "GET /web/api/devices/"
        },
    )


@router.get(
    "/{device_id}",
    summary="Детали устройства",
    responses={
        200: {"description": "Детали устройства и последние телеметрии"},
        401: {"description": "Не авторизован"},
        404: {"description": "Устройство не найдено"},
        501: {"description": "Ещё не реализовано"},
    },
)
async def get_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Возвращает детали устройства и последние N записей телеметрии."""
    return JSONResponse(
        status_code=501,
        content={
            "detail": "not implemented",
            "endpoint": f"GET /web/api/devices/{device_id}",
        },
    )


@router.post(
    "/{device_id}/command",
    summary="Отправить команду устройству",
    responses={
        200: {"description": "Команда отправлена"},
        401: {"description": "Не авторизован"},
        404: {"description": "Устройство не найдено"},
        502: {"description": "Шлюз недоступен"},
        501: {"description": "Ещё не реализовано"},
    },
)
async def send_command(
    device_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    Отправка команды на шлюз.

    Проксирует команду на HTTP-адаптер шлюза:
    POST http://{gateway_http_url}/api/v1/devices/{device_id}/command
    """
    return JSONResponse(
        status_code=501,
        content={
            "detail": "not implemented",
            "endpoint": f"POST /web/api/devices/{device_id}/command",
        },
    )
