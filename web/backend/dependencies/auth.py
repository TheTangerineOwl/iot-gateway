"""FastAPI dependency для проверки JWT-токена в защищённых эндпоинтах."""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from web.backend.dependencies.database import get_session
from web.backend.dependencies.config import Settings, get_settings
from web.backend.models.user import User
from web.backend.services.auth import verify_token


logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/web/api/auth/login")


async def _get_user(
    db: AsyncSession,
    username: str
):
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_session)
) -> User:
    """
    Извлекает и верифицирует JWT из заголовка Authorization.

    Raises:
        HTTPException(401): если токен отсутствует, невалиден или истёк.

    Returns:
        Пользователь (User).
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
    username = payload.get('sub')
    if username is None:
        raise credentials_exception
    user = await _get_user(db, username=username)
    if user is None:
        raise credentials_exception
    return user
