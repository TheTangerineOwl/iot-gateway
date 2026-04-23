"""
Роутер статуса шлюза.

Эндпоинты:
  GET /web/api/gateway/status  — статус адаптеров и очереди сообщений
  GET /web/api/gateway/config  — базовая конфигурация шлюза
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from web.backend.models.user import User
from web.backend.dependencies.auth import get_current_user


router = APIRouter(tags=["gateway"])


@router.get(
    "/status",
    summary="Статус шлюза и адаптеров",
    responses={
        200: {"description": "Статус шлюза"},
        401: {"description": "Не авторизован"},
        501: {"description": "Ещё не реализовано"},
    },
)
async def get_gateway_status(
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    Получение статуса шлюза.

    Возвращает статус адаптеров (HTTP, WebSocket, CoAP, MQTT),
    uptime шлюза и размер очереди сообщений.
    """
    return JSONResponse(
        status_code=501,
        content={
            "detail": "not implemented",
            "endpoint": "GET /web/api/gateway/status"
        },
    )


@router.get(
    "/config",
    summary="Базовая конфигурация шлюза",
    responses={
        200: {"description": "Конфигурация шлюза"},
        401: {"description": "Не авторизован"},
        501: {"description": "Ещё не реализовано"},
    },
)
async def get_gateway_config(
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    Получение конфигурации шлюза.

    Возвращает базовую конфигурацию шлюза: порты, имена, без секретов.
    """
    return JSONResponse(
        status_code=501,
        content={
            "detail": "not implemented",
            "endpoint": "GET /web/api/gateway/config"
        },
    )
