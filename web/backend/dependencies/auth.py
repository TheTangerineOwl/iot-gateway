"""
FastAPI dependency для проверки JWT-токена в защищённых эндпоинтах.

Использование:
    @router.get("/protected")
    async def protected(user: dict = Depends(get_current_user)):
        return {"username": user["sub"]}
"""
import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from web.backend.dependencies.config import Settings, get_settings
from web.backend.services.auth import verify_token

logger = logging.getLogger(__name__)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/web/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Извлекает и верифицирует JWT из заголовка Authorization.

    Raises:
        HTTPException(401): если токен отсутствует, невалиден или истёк.

    Returns:
        Payload токена (dict), содержащий как минимум поле "sub" (username).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось верифицировать токен",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_token(token, settings.secret_key)
    if payload is None:
        logger.warning("Попытка доступа с невалидным токеном")
        raise credentials_exception

    return payload
