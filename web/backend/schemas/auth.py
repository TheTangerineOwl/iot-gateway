"""Модели для авторизации."""
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """Модель запроса для входа."""

    model_config = ConfigDict(from_attributes=True)

    username: str = Field(
        ...,
        min_length=1,
        json_schema_extra={
            'example': 'username'
        }
    )
    password: str = Field(
        ...,
        min_length=8,
        json_schema_extra={
            'example': '********'
        }
    )


class LoginUserMe(BaseModel):
    """Модель запроса для входа."""

    model_config = ConfigDict(from_attributes=True)

    username: str = Field(
        ...,
        min_length=1,
        json_schema_extra={
            'example': 'username'
        }
    )
    id: int = Field(
        ...,
        ge=0
    )


class TokenResponse(BaseModel):
    """Ответ на запрос входа с токеном."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(...)
    token_type: str = Field(
        default="bearer"
    )
    expires_in: int = Field(
        ...,
        json_schema_extra={'example': 3600}
    )
