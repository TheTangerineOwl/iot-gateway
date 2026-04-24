"""
Роутер статуса шлюза.

Эндпоинты:
  GET /web/api/gateway/status  — статус адаптеров и очереди сообщений
  GET /web/api/gateway/config  — базовая конфигурация шлюза
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from web.backend.dependencies.auth import get_current_user
from web.backend.dependencies.config import Settings, get_settings
from web.backend.models.user import User
from web.backend.schemas.gateway.status import GatewayStatus
from web.backend.schemas.gateway.config import GatewayConfig
from web.backend.services.gateway import (
    fetch_gateway_config,
    fetch_gateway_status
)

router = APIRouter(tags=["gateway"])


@router.get(
    "/status",
    response_model=GatewayStatus,
    summary="Статус шлюза и адаптеров",
    responses={
        200: {"description": "Статус шлюза"},
        401: {"description": "Не авторизован"},
        500: {"description": "Не удалось получить статус шлюза"}
    },
)
async def get_gateway_status(
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> GatewayStatus | JSONResponse:
    """Возвращает текущий статус шлюза."""
    status = await fetch_gateway_status(settings)
    if not status:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "не удалось получить статус шлюза",
                "endpoint": "GET /web/api/gateway/status"
            },
        )
    return status


@router.get(
    "/config",
    response_model=GatewayConfig,
    summary="Базовая конфигурация шлюза",
    responses={
        200: {"description": "Конфигурация шлюза"},
        401: {"description": "Не авторизован"},
        500: {"description": "Не удалось получить конфигурацию шлюза"}
    },
)
async def get_gateway_config(
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> GatewayConfig | JSONResponse:
    """Возвращает базовую конфигурацию шлюза."""
    config = await fetch_gateway_config(settings)
    if not config:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "не удалось получить конфигурацию шлюза",
                "endpoint": "GET /web/api/gateway/config"
            },
        )
    return config
