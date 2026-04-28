"""CRUD операции для работы с пользователями."""
import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.models.user import User
from web.backend.services.auth import get_password_hash, verify_password


logger = logging.getLogger(__name__)


async def get_user_by_username(
    db: AsyncSession,
    username: str,
) -> Optional[User]:
    """
    Получить пользователя по username.

    Returns:
        User или None, если не найден.
    """
    result = await db.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(
    db: AsyncSession,
    user_id: int,
) -> Optional[User]:
    """
    Получить пользователя по ID.

    Returns:
        User или None, если не найден.
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    username: str,
    password: str,
    is_active: bool = True,
) -> User:
    """
    Создать нового пользователя.

    Args:
        db: сессия БД
        username: имя пользователя (уникальное)
        password: пароль в plain-text (будет хэширован)
        is_active: активен ли пользователь

    Returns:
        Созданный User

    Raises:
        IntegrityError: если username уже существует
    """
    password_hash = get_password_hash(password)

    user = User(
        username=username,
        password_hash=password_hash,
        is_active=is_active,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info("Создан пользователь: %s", username)
    return user


async def authenticate_user_db(
    db: AsyncSession,
    username: str,
    password: str,
) -> Optional[User]:
    """
    Аутентификация пользователя через БД.

    Args:
        db: сессия БД
        username: имя пользователя
        password: пароль (plain-text)

    Returns:
        User, если учётные данные верны, иначе None
    """
    user = await get_user_by_username(db, username)

    if user is None:
        logger.debug("Пользователь не найден: %s", username)
        return None

    if not user.is_active:
        logger.warning("Попытка входа неактивного пользователя: %s", username)
        return None

    if not verify_password(
        password, user.password_hash  # type: ignore[arg-type]
    ):
        logger.warning("Неверный пароль для пользователя: %s", username)
        return None

    return user


async def update_user_password(
    db: AsyncSession,
    user_id: int,
    new_password: str,
) -> Optional[User]:
    """
    Обновить пароль пользователя.

    Args:
        db: сессия БД
        user_id: ID пользователя
        new_password: новый пароль (plain-text, будет хэширован)

    Returns:
        Обновлённый User или None, если не найден
    """
    user = await get_user_by_id(db, user_id)

    if user is None:
        logger.warning("Пользователь с ID %d не найден", user_id)
        return None

    user.password_hash = get_password_hash(
        new_password
    )  # type: ignore[assignment]
    await db.commit()
    await db.refresh(user)

    logger.info("Обновлён пароль пользователя: %s", user.username)
    return user


async def deactivate_user(
    db: AsyncSession,
    user_id: int,
) -> Optional[User]:
    """
    Деактивировать пользователя.

    Returns:
        Обновлённый User или None
    """
    user = await get_user_by_id(db, user_id)

    if user is None:
        return None

    user.is_active = False  # type: ignore[assignment]
    await db.commit()
    await db.refresh(user)

    logger.info("Деактивирован пользователь: %s", user.username)
    return user


async def activate_user(
    db: AsyncSession,
    user_id: int,
) -> Optional[User]:
    """
    Активировать пользователя.

    Returns:
        Обновлённый User или None
    """
    user = await get_user_by_id(db, user_id)

    if user is None:
        return None

    user.is_active = True  # type: ignore[assignment]

    await db.commit()
    await db.refresh(user)

    logger.info("Активирован пользователь: %s", user.username)
    return user
