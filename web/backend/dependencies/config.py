"""Чтение конфигурации для веб-приложения."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Модель с настройками.

    Читает переменные окружения с префиксом WEB__
    Пример: WEB__SECRET_KEY=changeme → settings.secret_key == "changeme"
    """

    host: str = "0.0.0.0"
    port: int = 8090

    secret_key: str = "changeme-in-prod"
    admin_user: str = "admin"
    admin_password: str = "changeme"
    token_expire_minutes: int = 60

    gateway_http_url: str = "http://localhost:8081"
    gateway_ws_url: str = "http://localhost:8082"
    logs_dir: str = "logs/"

    # Настройки хранилища (read-only, для devices сервиса)
    sqlite_dbpath: str = "data/telemetry.db"

    model_config = SettingsConfigDict(
        env_prefix="WEB__",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Кешированный синглтон настроек.

    Используется как FastAPI Depends:
        settings: Settings = Depends(get_settings)
    """
    return Settings()
