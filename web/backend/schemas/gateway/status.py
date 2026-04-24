"""Схемы для получения публичной конфигурации шлюза."""
from datetime import datetime, timezone, timedelta
from pydantic import (
    BaseModel, ConfigDict, Field, AliasChoices, field_validator,
    ValidationError, computed_field
)
from typing import Optional, Union, Any, Dict
import logging


logger = logging.getLogger(__name__)


class BaseAdapterStatus(BaseModel):
    """Базовый возврат health-check адаптера."""

    model_config = ConfigDict(from_attributes=True, extra='allow')

    protocol: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('protocol', 'adapter', 'name'),
        json_schema_extra={
            'example': 'HTTP'
        }
    )
    running: Optional[bool] = Field(
        default=False,
        validation_alias=AliasChoices('running', 'on')
    )


class WebSocketStatus(BaseAdapterStatus):
    """Возврат health-check WebSocket-адаптера."""

    connections: Optional[int] = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices('connections', 'conn_count')
    )


class MQTTStatus(BaseAdapterStatus):
    """Возврат health-check MQTT-адаптера."""

    connected: Optional[bool] = Field(
        default=False,
        validation_alias=AliasChoices('connected')
    )
    broker: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('broker'),
        json_schema_extra={
            'example': 'http://localhost:8000'
        }
    )


AdapterStatusType = Union[
    BaseAdapterStatus | WebSocketStatus | MQTTStatus
]


class PipelineStatus(BaseModel):
    """Возврат статуса конвейера обработки."""

    model_config = ConfigDict(from_attributes=True, extra='allow')

    stages: Optional[int] = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices('stages', 'stage_count')
    )
    processed: Optional[int] = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices(
            'processed',
            'processed_count',
            'finished',
            'finished_count'
        )
    )
    filtered: Optional[int] = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices(
            'filtered',
            'filtered_count',
            'rejected',
            'rejected_count'
        )
    )
    errors: Optional[int] = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices('errors', 'error_count')
    )


class MessageBusStatus(BaseModel):
    """Возврат статуса шины сообщений."""

    model_config = ConfigDict(from_attributes=True, extra='allow')

    published: Optional[int] = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices(
            'published',
            'published_count'
        )
    )
    delivered: Optional[int] = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices(
            'delivered',
            'delivered_count',
            'received',
            'received_count'
        )
    )
    errors: Optional[int] = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices('errors', 'error_count')
    )
    queue_size: Optional[int] = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices('queue_size', 'queue', 'queue_count')
    )
    max_queue: Optional[int] = Field(
        default=None,
        gt=0,
        validation_alias=AliasChoices('max_queue', 'max_size', 'max_len')
    )
    subscribers: Optional[int] = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices('subscribers', 'listeners')
    )


class RegistryStatus(BaseModel):
    """Возврат статуса регистра устройств."""

    model_config = ConfigDict(from_attributes=True, extra='allow')

    total: Optional[int] = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices('total', 'count', 'device_count')
    )
    online_count: Optional[int] = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices(
            'total_online',
            'online_count',
            'online'
        )
    )


class GeneralGatewayStatus(BaseModel):
    """Базовый статус шлюза."""

    id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('id', 'gateway_id'),
        json_schema_extra={
            'example': '1'
        }
    )
    name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('name', 'gateway_name'),
        json_schema_extra={
            'example': 'IoT Gateway'
        }
    )
    running: Optional[bool] = Field(
        default=False,
        validation_alias=AliasChoices('running', 'on')
    )
    start_time: Optional[datetime] = Field(
        default=None,
        validation_alias=AliasChoices('start_time', 'started_at'),
        json_schema_extra={
            'example': '2026-04-24T20:00:00Z'
        }
    )

    @field_validator('start_time', mode='before')
    @classmethod
    def validate_start_time(cls, v: datetime | str) -> datetime:
        """Валидация времени старта шлюза."""
        if isinstance(v, str):
            val = datetime.fromisoformat(v)
        else:
            val = v
        now = datetime.now(tz=timezone.utc)
        if val.tzinfo is None:
            orig = val.replace(tzinfo=timezone.utc)
        else:
            orig = val.astimezone(timezone.utc)
        if datetime.now(tz=timezone.utc) < orig:
            logger.warning(
                'Ошибка валидации для start_time: '
                'start_time не может быть в будущем'
            )
            return now
        return orig


def _create_adapter_status(
    key: str,
    data: Dict[str, Any]
) -> AdapterStatusType:
    """Фабрика для создания статуса адаптера по имени протокола."""
    adapter_mapping = {
        'mqtt': MQTTStatus,
        'websocket': WebSocketStatus,
    }
    adapter_class = adapter_mapping.get(key, BaseAdapterStatus)
    return adapter_class(**data)


class GatewayStatus(BaseModel):
    """Вывод статуса шлюза."""

    model_config = ConfigDict(from_attributes=True, extra='allow')

    general: Optional[GeneralGatewayStatus] = Field(
        default=None,
        validation_alias=AliasChoices('general', 'main', 'gateway')
    )

    devices: Optional[RegistryStatus] = Field(
        default=None,
        validation_alias=AliasChoices(
            'devices',
            'registry',
            'device_stats',
            'device_registry'
        )
    )

    bus: Optional[MessageBusStatus] = Field(
        default=None,
        validation_alias=AliasChoices(
            'message_bus',
            'bus',
            'bus_stats'
        )
    )

    pipeline: Optional[PipelineStatus] = Field(
        default=None,
        validation_alias=AliasChoices(
            'pipeline',
            'stages',
            'pipeline_stats'
        )
    )

    adapters: Optional[dict[str, AdapterStatusType]] = Field(
        default=None,
        validation_alias=AliasChoices('adapters', 'protocols')
    )

    @field_validator('adapters', mode='before')
    @classmethod
    def validate_adapters(
        cls,
        v: Optional[dict[str, Any]]
    ) -> Dict[str, AdapterStatusType]:
        """Валидация поля adapters."""
        if v is None:
            return {}
        result = {}
        for key, val in v.items():
            try:
                res = _create_adapter_status(key.lower(), val)
            except ValidationError as ve:
                logger.exception(
                    f"Ошибка валидации для статуса адаптера '{key}': {ve}"
                )
                res = BaseAdapterStatus(running=False)
            except Exception as ex:
                logger.exception(
                    f"Ошибка для статуса адаптера '{key}': {ex}"
                )
                res = BaseAdapterStatus(running=False)
            result[key] = res
        return result

    @computed_field(  # type: ignore[prop-decorator]
        json_schema_extra={
            'example': '2026-04-24T21:00:00Z'
        }
    )
    @property
    def checked_at(self) -> datetime:
        return datetime.now(timezone.utc)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def uptime(self) -> timedelta:
        now = datetime.now(timezone.utc)
        if self.general and self.general.start_time:
            return now - self.general.start_time
        return now - now
