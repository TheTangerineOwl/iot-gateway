"""Функции для отправки запросов на менеджмент-адаптер шлюза."""
import logging
from aiohttp import (
    ClientSession, ClientTimeout, ClientPayloadError
)
from http import HTTPStatus
from typing import Any, Optional


logger = logging.getLogger(__name__)


async def send_post(
    url: str,
    payload: dict[str, Any],
    timeout: float = 5.0
) -> tuple[int, Optional[dict]]:
    """
    Проксировать команду на management-адаптер шлюза.

    Returns:
        (http_status_code, response_body)
    """
    try:
        async with ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                timeout=ClientTimeout(total=timeout),
            ) as resp:
                body = await resp.json(content_type=None)
                return resp.status, body
    except Exception as exc:
        logger.warning("Не удалось отправить команду на шлюз: %s", exc)
        return HTTPStatus.BAD_GATEWAY, None


async def send_get(
    url: str,
    timeout: float = 5.0,
) -> tuple[bool, Optional[dict]]:
    """
    Делает GET-запрос к эндпоинту шлюза.

    Returns:
        (True, request body) — если статус 200
        (False, None) — если недоступен или ошибка
    """
    try:
        async with ClientSession() as session:
            async with session.get(
                url,
                timeout=ClientTimeout(total=timeout),
            ) as resp:
                if resp.status == HTTPStatus.OK:
                    body = await resp.json(content_type=None)
                    return True, body
                return False, None
    except Exception as exc:
        logger.debug("Health-check %s недоступен: %s", url, exc)
        return False, None


async def fetch_from_gateway(
    url: str,
    check_timeout: float = 5.0
) -> dict:
    """Получить ответ шлюза на запрос через менеджмент-адаптер."""
    ok, body = await send_get(url, check_timeout)
    if not ok:
        raise TimeoutError('Не удалось подключиться к шлюзу')
    if not body:
        raise ClientPayloadError('Не удалось получить тело запроса')
    return body
