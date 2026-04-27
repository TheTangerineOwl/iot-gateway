"""Чтение конфигурации для веб-приложения."""
import logging
from functools import lru_cache
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Модель с настройками.

    Читает переменные окружения с префиксом WEB__
    Пример: WEB__SECRET_KEY=changeme → settings.secret_key == "changeme"
    """

    gateway_id: str = '1'
    gateway_name: str = 'IoT Gateway'
    host: str = "0.0.0.0"
    port: int = 8090

    secret_key: str = "changeme-in-prod"
    admin_user: str = "admin"
    admin_password: str = "changeme"
    token_expire_minutes: int = 60

    logs_dir: str = "logs/"

    sqlite_dbpath: str = "data/telemetry.db"

    gateway_management_url: str = 'http://localhost:8001'

    check_timeout: float = 5.0

    model_config = SettingsConfigDict(
        env_prefix="WEB__",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Кешированный синглтон настроек."""
    return Settings()


def get_database_url(settings: Settings) -> str:
    """
    Определяет URL БД из переменных окружения.

    Использует STORAGE__POSTGRESQL__* или STORAGE__SQLITE__DBPATH
    в зависимости от наличия переменных PostgreSQL.
    """
    # Проверяем наличие переменных PostgreSQL
    pg_host = os.getenv("STORAGE__POSTGRESQL__ADDRESS__HOST")
    pg_port = os.getenv("STORAGE__POSTGRESQL__ADDRESS__PORT", "5432")
    pg_user = os.getenv("STORAGE__POSTGRESQL__USER__USERNAME")
    pg_password = os.getenv("STORAGE__POSTGRESQL__USER__PASSWORD")
    pg_dbname = os.getenv("STORAGE__POSTGRESQL__DBNAME")
    use_db = os.getenv("GATEWAY__GENERAL__STORAGE_TYPE")

    if (
        use_db
        and use_db.lower() in ['postgres', 'postgresql']
        and all([pg_host, pg_user, pg_password, pg_dbname])
    ):
        # PostgreSQL async URL
        url = (
            f"postgresql+asyncpg://{pg_user}:{pg_password}"
            f"@{pg_host}:{pg_port}/{pg_dbname}"
        )
        logger.info("Используем PostgreSQL: %s@%s/%s",
                    pg_user, pg_host, pg_dbname)
        return url
    else:
        # SQLite async URL
        sqlite_path = settings.sqlite_dbpath
        url = f"sqlite+aiosqlite:///{sqlite_path}"
        logger.info("Используем SQLite: %s", sqlite_path)
        return url
