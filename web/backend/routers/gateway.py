"""
Роутер статуса шлюза.

Эндпоинты:
  GET /web/api/gateway/status  — статус адаптеров и очереди сообщений
  GET /web/api/gateway/config  — базовая конфигурация шлюза
"""
import logging
from aiohttp import ClientPayloadError
from http import HTTPStatus
from fastapi import APIRouter, Depends, HTTPException

from web.backend.dependencies.auth import get_current_user
from web.backend.dependencies.config import Settings, get_settings
from web.backend.models.user import User
from web.backend.schemas.gateway.status import GatewayStatus
from web.backend.schemas.gateway.config import GatewayConfig
from web.backend.services.gateway import (
    fetch_gateway_config,
    fetch_gateway_status
)


logger = logging.getLogger(__name__)
router = APIRouter(tags=["gateway"])


@router.get(
    "/status",
    response_model=GatewayStatus,
    summary="Статус шлюза и адаптеров",
    responses={
        HTTPStatus.OK:
            {"description": "Статус шлюза"},
        HTTPStatus.UNAUTHORIZED:
            {"description": "Не авторизован"},
        HTTPStatus.INTERNAL_SERVER_ERROR:
            {"description": "Не удалось получить статус шлюза"},
        HTTPStatus.GATEWAY_TIMEOUT:
            {"description": "Health-check к шлюзу не вернул OK"},
        HTTPStatus.UNPROCESSABLE_ENTITY:
            {"description": "Шлюз не вернул статус"}
    },
)
async def get_gateway_status(
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> GatewayStatus:
    """Возвращает текущий статус шлюза."""
    error = False
    err_msg = 'Не удалось получить статус шлюза'
    status = HTTPStatus.OK
    try:
        gw_status = await fetch_gateway_status(settings)
    except TimeoutError as te:
        error = True
        status = HTTPStatus.GATEWAY_TIMEOUT
        err_msg += f': {te}'
    except ClientPayloadError as cpe:
        error = True
        status = HTTPStatus.UNPROCESSABLE_ENTITY
        err_msg += f': {cpe}'
    except Exception:
        error = True
        status = HTTPStatus.INTERNAL_SERVER_ERROR
    finally:
        if error:
            logger.exception(err_msg)
            raise HTTPException(
                status_code=status,
                detail=err_msg
            )
    return gw_status


@router.get(
    "/config",
    response_model=GatewayConfig,
    summary="Базовая конфигурация шлюза",
    responses={
        HTTPStatus.OK:
            {"description": "Конфигурация шлюза"},
        HTTPStatus.UNAUTHORIZED:
            {"description": "Не авторизован"},
        HTTPStatus.INTERNAL_SERVER_ERROR:
            {"description": "Не удалось получить конфигурацию шлюза"},
        HTTPStatus.GATEWAY_TIMEOUT:
            {"description": "Health-check к шлюзу не вернул OK"},
        HTTPStatus.UNPROCESSABLE_ENTITY:
            {"description": "Шлюз не вернул конфигурацию"}
    },
)
async def get_gateway_config(
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> GatewayConfig:
    """Возвращает базовую конфигурацию шлюза."""
    error = False
    err_msg = 'Не удалось получить конфигурацию шлюза'
    status = HTTPStatus.OK
    try:
        gw_config = await fetch_gateway_config(settings)
    except TimeoutError as te:
        error = True
        status = HTTPStatus.GATEWAY_TIMEOUT
        err_msg += f': {te}'
    except ClientPayloadError as cpe:
        error = True
        status = HTTPStatus.UNPROCESSABLE_ENTITY
        err_msg += f': {cpe}'
    except Exception:
        error = True
        status = HTTPStatus.INTERNAL_SERVER_ERROR
    finally:
        if error:
            logger.exception(err_msg)
            raise HTTPException(
                status_code=status,
                detail=err_msg
            )
    return gw_config
