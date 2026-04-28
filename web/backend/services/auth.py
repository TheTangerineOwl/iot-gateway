"""
Сервис авторизации: JWT-токены и проверка паролей.

Поддерживает два формата WEB__ADMIN_PASSWORD:
  - bcrypt-хэш (начинается с $2b$) - сравниваем через passlib
  - plain-text - прямое сравнение строк (только для dev/demo)
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from jose import JWTError, jwt
import bcrypt


logger = logging.getLogger(__name__)

ALGORITHM = "HS256"


def get_password_hash(plain_password: str) -> str:
    """Возвращает bcrypt-хэш пароля."""
    if not plain_password:
        raise ValueError('Need password')
    byte_pass = plain_password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(byte_pass, salt)
    return hashed.decode('utf-8')


def _is_bcrypt_hash(value: str) -> bool:
    """Определяет, является ли строка bcrypt-хэшем."""
    return value.startswith(("$2b$", "$2a$", "$2y$"))


def verify_password(plain_password: str, stored_password: str) -> bool:
    """
    Проверяет пароль против сохранённого значения.

    stored_password может быть bcrypt-хэшем или plain-text строкой.
    """
    if _is_bcrypt_hash(stored_password):
        try:
            byte_pass = plain_password.encode('utf-8')[:72]
            stored_bytes = stored_password.encode('utf-8')
            return bcrypt.checkpw(byte_pass, stored_bytes)
        except Exception:
            logger.warning("Ошибка при верификации bcrypt-хэша")
            return False
    else:
        return plain_password == stored_password


def authenticate_user(
    username: str,
    password: str,
    expected_username: str,
    expected_password: str,
) -> bool:
    """
    Проверяет учётные данные пользователя.

    Возвращает True только если username и password совпадают.
    """
    if not username or not password:
        logger.info("Попытка аутентификации с пустыми учётными данными")
        return False
    if username != expected_username:
        logger.info("Неверное имя пользователя: %s", username)
        return False
    return verify_password(password, expected_password)


def create_access_token(
    data: dict[str, Any],
    secret_key: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Создаёт JWT access token.

    Args:
        data: полезная нагрузка (payload). Обычно {"sub": username}.
        secret_key: секретный ключ из WEB__SECRET_KEY.
        expires_delta: время жизни токена. По умолчанию 60 минут.

    Returns:
        Подписанный JWT-токен в виде строки.
    """
    to_encode = data.copy()
    expire = datetime.now(tz=timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=60)
    )
    to_encode["exp"] = expire
    to_encode["iat"] = datetime.now(tz=timezone.utc)

    return jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)


def verify_token(token: str, secret_key: str) -> Optional[dict[str, Any]]:
    """
    Верифицирует JWT-токен и возвращает payload.

    Returns:
        Словарь с payload, если токен валиден.
        None, если токен невалиден или истёк.
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        # Проверяем наличие обязательного поля sub
        if payload.get("sub") is None:
            logger.warning("JWT без поля 'sub'")
            return None
        return payload
    except JWTError as exc:
        logger.debug("JWT верификация провалена: %s", exc)
        return None
