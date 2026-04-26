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
from http import HTTPStatus
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.models.user import User
from web.backend.dependencies.auth import get_current_user
from web.backend.dependencies.config import Settings, get_settings
from web.backend.dependencies.database import get_session
from web.backend.schemas.devices import (
    DeviceList,
    DeviceTelemetry,
    CommandRequest, CommandResponse
)
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
    response_model=DeviceList,
    responses={
        HTTPStatus.OK: {"description": "Список устройств"},
        HTTPStatus.UNAUTHORIZED: {"description": "Не авторизован"},
        HTTPStatus.GATEWAY_TIMEOUT: {"description": "Шлюз недоступен"},
        HTTPStatus.INTERNAL_SERVER_ERROR:
            {"description": "Не удалось получить устройства"}
    },
)
async def list_devices(
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> DeviceList:
    """Возвращает список всех зарегистрированных устройств из реестра шлюза."""
    error = False
    status = HTTPStatus.OK
    err_msg = 'Не удалось получить устройства: '
    try:
        devices = await fetch_devices(settings)
    except TimeoutError as te:
        error = True
        status = HTTPStatus.GATEWAY_TIMEOUT
        err_msg += f': {te}'
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
    return devices


@router.get(
    "/{device_id}",
    summary="Детали устройства",
    response_model=DeviceTelemetry,
    responses={
        HTTPStatus.OK:
            {"description": "Детали устройства и последняя телеметрия"},
        HTTPStatus.UNAUTHORIZED:
            {"description": "Не авторизован"},
        HTTPStatus.NOT_FOUND:
            {"description": "Устройство не найдено"},
        HTTPStatus.GATEWAY_TIMEOUT: {"description": "Шлюз недоступен"},
        HTTPStatus.INTERNAL_SERVER_ERROR:
            {"description": "Не удалось получить устройство"}
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
) -> DeviceTelemetry:
    """Возвращает детали устройства и последние N записей телеметрии."""
    error = False
    status = HTTPStatus.OK
    err_msg = 'Не удалось получить устройство'
    try:
        device = await fetch_device(settings, device_id)
    except TimeoutError as te:
        error = True
        status = HTTPStatus.GATEWAY_TIMEOUT
        err_msg += f': {te}'
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

    err_msg = 'Не удалось получить телеметрию'
    try:
        telemetry = await fetch_last_telemetry(db, device_id, limit=limit)
        result = DeviceTelemetry(device=device, telemetry=telemetry)
    except ValueError as te:
        error = True
        status = HTTPStatus.BAD_REQUEST
        err_msg += f': {te}'
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
    return result


@router.post(
    "/{device_id}/command",
    response_model=CommandResponse,
    summary="Отправить команду устройству",
    responses={
        HTTPStatus.OK:
            {"description": "Команда отправлена, получен ответ"},
        HTTPStatus.BAD_REQUEST:
            {"description": "Некорректное тело запроса"},
        HTTPStatus.UNAUTHORIZED:
            {"description": "Не авторизован"},
        HTTPStatus.GATEWAY_TIMEOUT:
            {"description": "Устройство не ответило за отведённое время"},
    },
)
async def send_command(
    device_id: str,
    body: CommandRequest,
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> CommandResponse:
    """
    Проксирует команду на management-адаптер шлюза.

    POST {gateway_management_url}/management/devices/{device_id}/command
    """
    error = False
    status = HTTPStatus.OK
    err_msg = 'Ошибка отправки команды'
    try:
        response = await send_device_command(
            settings=settings,
            device_id=device_id,
            request=body
        )
    except ValueError as ve:
        error = True
        status = HTTPStatus.BAD_REQUEST
        err_msg += f': {ve}'
    except TimeoutError as te:
        error = True
        status = HTTPStatus.GATEWAY_TIMEOUT
        err_msg += f': {te}'
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
    return response
