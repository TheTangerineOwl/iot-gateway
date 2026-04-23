"""
Роутер авторизации.

Эндпоинты:
  POST /web/api/auth/login   — получить JWT-токен
  POST /web/api/auth/logout  — инвалидировать сессию (stateless stub)
"""
import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from web.backend.dependencies.auth import get_current_user
from web.backend.dependencies.config import Settings, get_settings
from web.backend.models.auth import LoginRequest, TokenResponse
from web.backend.services.auth import authenticate_user, create_access_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Получить JWT access token",
    responses={
        200: {"description": "Успешная авторизация"},
        401: {"description": "Неверные учётные данные"},
    },
)
async def login(
    request: LoginRequest,
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """
    Проверяет username/password против WEB__ADMIN_USER / WEB__ADMIN_PASSWORD.

    Возвращает Bearer JWT при успехе, 401 при ошибке.
    """
    valid = authenticate_user(
        username=request.username,
        password=request.password,
        expected_username=settings.admin_user,
        expected_password=settings.admin_password,
    )

    if not valid:
        logger.warning(
            "Неудачная попытка входа для пользователя: %s",
            request.username
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expire_delta = timedelta(minutes=settings.token_expire_minutes)
    token = create_access_token(
        data={"sub": request.username},
        secret_key=settings.secret_key,
        expires_delta=expire_delta,
    )

    logger.info("Пользователь '%s' успешно авторизован", request.username)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.token_expire_minutes * 60,
    )


@router.post(
    "/logout",
    summary="Выйти (инвалидировать токен на клиенте)",
    responses={
        200: {"description": "Успешный выход"},
        401: {"description": "Не авторизован"},
    },
)
async def logout(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Stateless logout: клиент должен удалить токен из хранилища."""
    logger.info("Пользователь '%s' вышел из системы", current_user.get("sub"))
    return {"message": "logged out"}
