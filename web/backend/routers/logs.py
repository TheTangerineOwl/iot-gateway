"""
Роутер логов.

Эндпоинты:
  GET /web/api/logs/list          — список лог-файлов в GATEWAY__LOGGER__DIR
  GET /web/api/logs/{filename}    — содержимое файла (с фильтрацией)
  GET /web/api/logs/stream        — SSE live-стрим активного лога
"""
import logging
from http import HTTPStatus
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from web.backend.models.user import User
from web.backend.dependencies.auth import get_current_user
from web.backend.dependencies.config import Settings, get_settings
from web.backend.schemas.logs import LogFileList, LogLines
from web.backend.services.logs import (
    read_log_list, read_log_file, read_stream_logs
)


logger = logging.getLogger(__name__)
router = APIRouter(tags=["logs"])


@router.get(
    "/list",
    response_model=LogFileList,
    summary="Список лог-файлов",
    responses={
        HTTPStatus.OK:
            {"description": "Список файлов в директории логов"},
        HTTPStatus.UNAUTHORIZED:
            {"description": "Не авторизован"},
        HTTPStatus.NOT_FOUND:
            {"description": "Директория не найдена"},
        HTTPStatus.INTERNAL_SERVER_ERROR:
            {"description": "Не удалось получить список файлов логов"},
    },
)
async def list_log_files(
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings)
) -> LogFileList:
    """
    Получение списка логов.

    Возвращает список лог-файлов из директории WEB__LOGS_DIR
    (совпадает с GATEWAY__LOGGER__DIR).
    """
    error = False
    err_msg = 'Не удалось получить список файлов логов'
    status = HTTPStatus.OK
    try:
        logs = await read_log_list(settings)
    except FileNotFoundError as fnf:
        error = True
        status = HTTPStatus.NOT_FOUND
        err_msg += f': {fnf}'
    except Exception as exc:
        error = True
        status = HTTPStatus.INTERNAL_SERVER_ERROR
        logger.exception(f'{err_msg}: {exc}')
    finally:
        if error:
            logger.exception(err_msg)
            raise HTTPException(
                status_code=status,
                detail=err_msg
            )
    return logs


@router.get(
    "/stream",
    response_class=StreamingResponse,
    summary="Live SSE стрим активного лога",
    responses={
        HTTPStatus.OK:
            {"description": "Server-Sent Events stream"},
        HTTPStatus.UNAUTHORIZED:
            {"description": "Не авторизован"},
        HTTPStatus.NOT_FOUND:
            {"description": "Файл не найден"},
        HTTPStatus.INTERNAL_SERVER_ERROR:
            {"description": "Не удалось получить поток лога"},
    },
)
async def stream_logs(
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    level: str = "INFO",
) -> StreamingResponse:
    """
    Получение потока логов.

    Server-Sent Events (text/event-stream): tail -f активного лог-файла.
    Фильтрация по уровню: level=INFO|WARNING|ERROR|DEBUG|CRITICAL
    """
    error = False
    err_msg = 'Не удалось получить поток лога'
    status = HTTPStatus.OK
    try:
        gen = await read_stream_logs(settings, level)
    except FileNotFoundError as fnf:
        error = True
        status = HTTPStatus.NOT_FOUND
        err_msg += f': {fnf}'
    except Exception as exc:
        error = True
        status = HTTPStatus.INTERNAL_SERVER_ERROR
        logger.exception(f'{err_msg}: {exc}')
    finally:
        if error:
            logger.exception(err_msg)
            raise HTTPException(
                status_code=status,
                detail=err_msg
            )
    return StreamingResponse(
        gen,
        status_code=status,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # отключает буферизацию в nginx
        },
    )


@router.get(
    "/{filename}",
    summary="Содержимое лог-файла",
    response_model=LogLines,
    responses={
        HTTPStatus.OK:
            {"description": "Строки лог-файла"},
        HTTPStatus.BAD_REQUEST:
            {"description": "Некорректные параметры запроса"},
        HTTPStatus.UNAUTHORIZED:
            {"description": "Не авторизован"},
        HTTPStatus.NOT_FOUND:
            {"description": "Файл не найден"},
        HTTPStatus.FORBIDDEN:
            {"description": "Доступ запрещён (path traversal)"},
        HTTPStatus.INTERNAL_SERVER_ERROR:
            {"description": "Не удалось получить содержимое файла"},
    },
)
async def get_log_file(
    filename: str,
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    lines: int = 100,
    level: str | None = None,
    search: str | None = None,
) -> LogLines:
    """
    Возвращает содержимое лог-файла с опциональной фильтрацией.

    Query params:
      - lines=100     — количество последних строк
      - level=INFO    — фильтр по уровню (INFO/WARNING/ERROR/DEBUG/CRITICAL)
      - search=текст  — текстовый поиск по строкам
    """
    error = False
    err_msg = 'Не удалось получить содержимое файла'
    status = HTTPStatus.OK
    try:
        log_file = await read_log_file(
            filename,
            settings,
            lines=lines,
            level=level,
            search=search
        )
    except PermissionError as pe:
        error = True
        err_msg += f': {pe}'
        status = HTTPStatus.FORBIDDEN
    except FileNotFoundError as fnf:
        error = True
        err_msg += f': {fnf}'
        status = HTTPStatus.NOT_FOUND
    except ValueError as ve:
        error = True
        err_msg += f': {ve}'
        status = HTTPStatus.BAD_REQUEST
    except Exception as exc:
        error = True
        status = HTTPStatus.INTERNAL_SERVER_ERROR
        logger.exception(f'{err_msg}: {exc}')
    finally:
        if error:
            logger.exception(err_msg)
            raise HTTPException(
                status_code=status,
                detail=err_msg
            )
    return log_file
