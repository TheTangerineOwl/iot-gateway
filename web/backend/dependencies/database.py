"""
Модуль для работы с базой данных веб-приложения.

Подключается к той же БД, что и основной шлюз (SQLite или PostgreSQL).
Создаёт таблицу users и обеспечивает создание админа при старте.
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from web.backend.dependencies.config import Settings, get_database_url
from web.backend.services.auth import get_password_hash

logger = logging.getLogger(__name__)

Base = declarative_base()
_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


async def init_db(settings: Settings) -> None:
    """
    Инициализация БД: создание engine, таблиц и пользователя-админа.
    """
    global _engine, _session_maker

    db_url = get_database_url(settings)
    _engine = create_async_engine(
        db_url,
        echo=False,
        future=True,
    )

    _session_maker = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Создаём таблицы
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Таблицы БД созданы/проверены")

    # Создаём админа, если его нет
    await create_admin_user(settings)


async def create_admin_user(settings: Settings) -> None:
    """
    Создаёт пользователя-админа из .env, если его ещё нет в БД.
    """
    if _session_maker is None:
        raise RuntimeError("БД не инициализирована")

    admin_username = settings.admin_user
    admin_password = settings.admin_password

    # Если пароль уже хэширован, используем его как есть
    # Иначе хэшируем
    if not admin_password.startswith("$2b$"):
        password_hash = get_password_hash(admin_password)
    else:
        password_hash = admin_password

    async with _session_maker() as session:
        # Проверяем, существует ли админ
        result = await session.execute(
            text("SELECT id FROM users WHERE username = :username"),
            {"username": admin_username}
        )
        existing = result.first()

        if existing:
            logger.info(
                "Пользователь-админ '%s' уже существует",
                admin_username
            )
        else:
            # Создаём админа
            await session.execute(
                text(
                    "INSERT INTO users (username, password_hash, is_active) "
                    "VALUES (:username, :password_hash, :is_active)"
                ),
                {
                    "username": admin_username,
                    "password_hash": password_hash,
                    "is_active": True,
                }
            )
            await session.commit()
            logger.info("Создан пользователь-админ: %s", admin_username)


async def close_db() -> None:
    """Закрывает соединение с БД."""
    global _engine, _session_maker

    if _engine:
        await _engine.dispose()
        _engine = None
        _session_maker = None
        logger.info("Соединение с БД закрыто")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Контекстный менеджер для получения сессии БД.

    Использование:
        async with get_db_session() as session:
            result = await session.execute(...)
    """
    if _session_maker is None:
        raise RuntimeError("БД не инициализирована.")

    async with _session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для FastAPI endpoints.

    Использование:
        @router.get("/...")
        async def endpoint(db: AsyncSession = Depends(get_session)):
            ...
    """
    async with get_db_session() as session:
        yield session
