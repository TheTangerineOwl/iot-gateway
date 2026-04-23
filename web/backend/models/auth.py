"""Модели для авторизации."""
from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Модель запроса для входа."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Ответ на запрос входа с токеном."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
