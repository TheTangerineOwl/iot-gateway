"""
Роутер авторизации.

Эндпоинты:
  POST /web/api/auth/login   — получить JWT-токен
  POST /web/api/auth/logout  — инвалидировать сессию (stateless stub)
  GET  /web/api/auth/me      — получить информацию о текущем пользователе
"""
import logging
from datetime import timedelta
from http import HTTPStatus
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.dependencies.database import get_session
from web.backend.dependencies.auth import get_current_user
from web.backend.dependencies.config import Settings, get_settings
from web.backend.schemas.auth import TokenResponse, LoginUserMe
from web.backend.models.user import User
from web.backend.services.auth import create_access_token
from web.backend.services.user_service import authenticate_user_db


logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Получить JWT access token",
    responses={
        HTTPStatus.OK: {"description": "Успешная авторизация"},
        HTTPStatus.UNAUTHORIZED: {"description": "Неверные учётные данные"},
    },
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """
    Проверяет username/password через БД.

    Возвращает Bearer JWT при успехе, 401 при ошибке.
    """
    username = form_data.username
    password = form_data.password
    user = await authenticate_user_db(
        db=db,
        username=username,
        password=password,
    )

    if user is None:
        logger.warning(
            "Неудачная попытка входа для пользователя: %s",
            username
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expire_delta = timedelta(minutes=settings.token_expire_minutes)
    token = create_access_token(
        data={"sub": username, "user_id": user.id},
        secret_key=settings.secret_key,
        expires_delta=expire_delta,
    )

    logger.info("Пользователь '%s' успешно авторизован", username)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.token_expire_minutes * 60,
    )


@router.post(
    "/logout",
    summary="Выйти (инвалидировать токен на клиенте)",
    responses={
        HTTPStatus.OK: {"description": "Успешный выход"},
        HTTPStatus.UNAUTHORIZED: {"description": "Не авторизован"},
    },
)
async def logout(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Stateless logout: клиент должен удалить токен из хранилища."""
    logger.info("Пользователь '%s' вышел из системы", current_user.username)
    return {"message": "logged out"}


@router.get(
    "/me",
    response_model=LoginUserMe,
    summary="Получить информацию о текущем пользователе",
    responses={
        HTTPStatus.OK: {"description": "Информация о пользователе"},
        HTTPStatus.UNAUTHORIZED: {"description": "Не авторизован"},
    },
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> LoginUserMe:
    """
    Возвращает информацию о текущем авторизованном пользователе.

    Извлекает данные из JWT токена.
    """
    me = LoginUserMe(
        username=current_user.username,  # type: ignore[arg-type]
        id=current_user.id  # type: ignore[arg-type]
    )
    return me
