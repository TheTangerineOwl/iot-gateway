"""
Роутер логов.

Эндпоинты:
  GET /web/api/logs/list          — список лог-файлов в GATEWAY__LOGGER__DIR
  GET /web/api/logs/{filename}    — содержимое файла (с фильтрацией)
  GET /web/api/logs/stream        — SSE live-стрим активного лога
"""
import logging
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
        200: {"description": "Список файлов в директории логов"},
        401: {"description": "Не авторизован"},
        404: {"description": "Директория не найдена"},
        500: {"description": "Не удалось получить список файлов логов"},
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
    status = 200
    try:
        logs = await read_log_list(settings)
    except FileNotFoundError as fnf:
        error = True
        status = 404
        err_msg += f': {fnf}'
    except Exception as exc:
        error = True
        status = 500
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
        200: {"description": "Server-Sent Events stream"},
        401: {"description": "Не авторизован"},
        404: {"description": "Файл не найден"},
        500: {"description": "Не удалось получить поток лога"},
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
    status = 200
    try:
        gen = await read_stream_logs(settings, level)
    except FileNotFoundError as fnf:
        error = True
        status = 404
        err_msg += f': {fnf}'
    except Exception as exc:
        error = True
        status = 500
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
        200: {"description": "Строки лог-файла"},
        400: {"description": "Некорректные параметры запроса"},
        401: {"description": "Не авторизован"},
        404: {"description": "Файл не найден"},
        403: {"description": "Доступ запрещён (path traversal)"},
        500: {"description": "Не удалось получить содержимое файла"},
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
    status = 200
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
        status = 403
    except FileNotFoundError as fnf:
        error = True
        err_msg += f': {fnf}'
        status = 404
    except ValueError as ve:
        error = True
        err_msg += f': {ve}'
        status = 400
    except Exception as exc:
        error = True
        status = 500
        logger.exception(f'{err_msg}: {exc}')
    finally:
        if error:
            logger.exception(err_msg)
            raise HTTPException(
                status_code=status,
                detail=err_msg
            )
    return log_file
