"""Схемы для девайсов."""
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import (
    BaseModel, ConfigDict, Field, AliasChoices, field_validator
)


logger = logging.getLogger(__name__)


class Device(BaseModel):
    """Схема устройства."""

    model_config = ConfigDict(from_attributes=True, extra='allow')

    device_id: str = Field(
        ...,
        validation_alias=AliasChoices('device_id', 'id'),
        json_schema_extra={
            'example': 'dev-001'
        }
    )
    name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('name', 'device_name'),
        json_schema_extra={
            'example': 'test-device'
        }
    )
    protocol: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            'protocol',
            'protocol_type',
            'protocol_name'
        ),
        json_schema_extra={
            'example': 'HTTP'
        }
    )
    registered_at: Optional[datetime] = Field(
        default=None,
        validation_alias=AliasChoices('registered_at', 'created_at'),
        json_schema_extra={
            'example': '2026-04-24T20:00:00Z'
        }
    )
    last_seen: Optional[datetime] = Field(
        default=None,
        validation_alias=AliasChoices(
            'last_seen', 'last_update', 'last_response'
        ),
        json_schema_extra={
            'example': '2026-04-24T21:00:00Z'
        }
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        validation_alias=AliasChoices(
            'metadata', 'extra'
        )
    )

    @field_validator('registered_at', mode='before')
    @classmethod
    def validate_registered_at(
        cls, v: datetime | str | float
    ) -> datetime:
        """Валидация времени регистрации устройства."""
        if isinstance(v, str):
            val = datetime.fromisoformat(v)
        elif isinstance(v, float):
            val = datetime.fromtimestamp(v)
        else:
            val = v
        now = datetime.now(tz=timezone.utc)
        if val.tzinfo is None:
            orig = val.replace(tzinfo=timezone.utc)
        else:
            orig = val.astimezone(timezone.utc)
        if datetime.now(tz=timezone.utc) < orig:
            logger.warning(
                'Ошибка валидации для registered_at: '
                'registered_at не может быть в будущем'
            )
            return now
        return orig

    @field_validator('last_seen', mode='before')
    @classmethod
    def validate_last_seen(cls, v: datetime | str | float) -> datetime:
        """Валидация времени последней активности."""
        if isinstance(v, str):
            val = datetime.fromisoformat(v)
        elif isinstance(v, float):
            val = datetime.fromtimestamp(v)
        else:
            val = v
        now = datetime.now(tz=timezone.utc)
        if val.tzinfo is None:
            orig = val.replace(tzinfo=timezone.utc)
        else:
            orig = val.astimezone(timezone.utc)
        if datetime.now(tz=timezone.utc) < orig:
            logger.warning(
                'Ошибка валидации для last_seen: '
                'last_seen не может быть в будущем'
            )
            return now
        return orig


class DeviceList(BaseModel):
    """Схема для списка устройств."""

    model_config = ConfigDict(from_attributes=True)

    devices: list[Device] = Field(
        ...,
        validation_alias=AliasChoices(
            'devices', 'registry', 'results'
        ),
    )
    total: int = Field(
        default=0,
        ge=0,
        validation_alias=AliasChoices(
            'total', 'total_count', 'count'
        )
    )

    @field_validator('total', mode='before')
    @classmethod
    def validate_total(cls, v: int, info) -> int:
        """Валидация количества устройств."""
        devices = info.data.get('devices', [])
        if v != len(devices):
            raise ValueError(
                f'total ({v}) не соответствует '
                f'количеству файлов ({len(devices)})'
            )
        return v


class Telemetry(BaseModel):
    """Схема телеметрии."""

    model_config = ConfigDict(from_attributes=True, extra='allow')

    device_id: str = Field(
        ...,
        json_schema_extra={
            'example': 'dev-001'
        }
    )
    payload: dict[str, Any] = Field(
        ...,
        json_schema_extra={
            'example': {
                'value': 25.0,
                'type': 'temp',
                'unit': 'celsius'
            }
        }
    )
    timestamp: datetime = Field(
        ...,
        validation_alias=AliasChoices(
            'timestamp', 'time'
        ),
        json_schema_extra={
            'example': '2026-04-24T21:00:00Z'
        }
    )

    @field_validator('timestamp', mode='before')
    @classmethod
    def validate_timestamp(cls, v: datetime | str | float) -> datetime:
        """Валидация времени последней активности."""
        if isinstance(v, str):
            val = datetime.fromisoformat(v)
        elif isinstance(v, float):
            val = datetime.fromtimestamp(v)
        else:
            val = v
        now = datetime.now(tz=timezone.utc)
        if val.tzinfo is None:
            orig = val.replace(tzinfo=timezone.utc)
        else:
            orig = val.astimezone(timezone.utc)
        if datetime.now(tz=timezone.utc) < orig:
            logger.warning(
                'Ошибка валидации для timestamp: '
                'timestamp не может быть в будущем'
            )
            return now
        return orig


class TelemetryList(BaseModel):
    """Схема списка телеметрии."""

    model_config = ConfigDict(from_attributes=True)

    records: list[Telemetry] = Field(
        ...,
        validation_alias=AliasChoices(
            'telemetry', 'records'
        ),
    )
    total: int = Field(
        default=0,
        ge=0,
        validation_alias=AliasChoices(
            'total', 'total_count', 'count'
        )
    )

    @field_validator('total', mode='before')
    @classmethod
    def validate_total(cls, v: int, info) -> int:
        """Валидация количества записей."""
        records = info.data.get('telemetry', [])
        if v != len(records):
            raise ValueError(
                f'total ({v}) не соответствует '
                f'количеству файлов ({len(records)})'
            )
        return v


class DeviceTelemetry(BaseModel):
    """Устройство со своими записями телеметрии."""

    model_config = ConfigDict(from_attributes=True)

    device: Device = Field(..., alias='device')
    telemetry: TelemetryList = Field(..., alias='telemetry')


class CommandRequest(BaseModel):
    """Схема отправляемой команды."""

    model_config = ConfigDict(from_attributes=True)

    command: str = Field(
        ...,
        json_schema_extra={
            'example': 'ping'
        }
    )
    params: Optional[dict[str, Any]] = Field(
        default=None,
        json_schema_extra={
            'example': {
                'host': 'localhost'
            }
        }
    )
    timeout: float = Field(
        default=10,
        ge=0
    )
    # device_id: str = Field(
    #     ...,
    #     validation_alias=AliasChoices('device_id', 'device'),
    #     json_schema_extra={
    #         'example': 'dev-001'
    #     }
    # )


class CommandResponse(BaseModel):
    """Схема ответа на команду."""

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(
        ...,
        min_length=2,
        json_schema_extra={
            'example': 'delivered'
        }
    )
    device_id: str = Field(
        ...,
        validation_alias=AliasChoices('device_id', 'id'),
        json_schema_extra={
            'example': 'dev-001'
        }
    )
    command: str = Field(
        ...,
        validation_alias=AliasChoices('command', 'command_str'),
        json_schema_extra={
            'example': 'check_state --times 1'
        }
    )
    message_id: str = Field(
        ...,
        validation_alias=AliasChoices('message_id', 'message'),
        json_schema_extra={
            'example': 'msg-001'
        }
    )
    response: Optional[dict[str, Any]] = Field(
        default=None,
        json_schema_extra={
            'example': {
                'status': 'delivered'
            }
        }
    )
