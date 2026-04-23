"""
Роутер логов.

Эндпоинты:
  GET /web/api/logs/list          — список лог-файлов в GATEWAY__LOGGER__DIR
  GET /web/api/logs/{filename}    — содержимое файла (с фильтрацией)
  GET /web/api/logs/stream        — SSE live-стрим активного лога
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from web.backend.models.user import User
from web.backend.dependencies.auth import get_current_user


router = APIRouter(tags=["logs"])


@router.get(
    "/list",
    summary="Список лог-файлов",
    responses={
        200: {"description": "Список файлов в директории логов"},
        401: {"description": "Не авторизован"},
        501: {"description": "Ещё не реализовано"},
    },
)
async def list_log_files(
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    Получение списка логов.

    Возвращает список лог-файлов из директории WEB__LOGS_DIR
    (совпадает с GATEWAY__LOGGER__DIR).
    """
    return JSONResponse(
        status_code=501,
        content={
            "detail": "not implemented",
            "endpoint": "GET /web/api/logs/list"
        },
    )


@router.get(
    "/stream",
    summary="Live SSE стрим активного лога",
    responses={
        200: {"description": "Server-Sent Events stream"},
        401: {"description": "Не авторизован"},
        501: {"description": "Ещё не реализовано"},
    },
)
async def stream_logs(
    current_user: User = Depends(get_current_user),
    level: str = "INFO",
) -> JSONResponse:
    """
    Получение потока логов.

    Server-Sent Events (text/event-stream): tail -f активного лог-файла.
    Фильтрация по уровню: level=INFO|WARNING|ERROR|DEBUG|CRITICAL
    """
    return JSONResponse(
        status_code=501,
        content={
            "detail": "not implemented",
            "endpoint": "GET /web/api/logs/stream"
        },
    )


@router.get(
    "/{filename}",
    summary="Содержимое лог-файла",
    responses={
        200: {"description": "Строки лог-файла"},
        401: {"description": "Не авторизован"},
        404: {"description": "Файл не найден"},
        403: {"description": "Доступ запрещён (path traversal)"},
        501: {"description": "Ещё не реализовано"},
    },
)
async def get_log_file(
    filename: str,
    current_user: User = Depends(get_current_user),
    lines: int = 100,
    level: str | None = None,
    search: str | None = None,
) -> JSONResponse:
    """
    Возвращает содержимое лог-файла с опциональной фильтрацией.

    Query params:
      - lines=100     — количество последних строк
      - level=INFO    — фильтр по уровню (INFO/WARNING/ERROR/DEBUG/CRITICAL)
      - search=текст  — текстовый поиск по строкам
    """
    return JSONResponse(
        status_code=501,
        content={
            "detail": "not implemented",
            "endpoint": f"GET /web/api/logs/{filename}",
        },
    )
