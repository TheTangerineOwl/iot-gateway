"""Схемы для получения публичной конфигурации шлюза."""
from pydantic import (
    BaseModel, ConfigDict, Field, AliasChoices, field_validator,
    ValidationError
)
from typing import Optional, Union, Any, Dict
import logging


logger = logging.getLogger(__name__)


class GeneralGatewayConfig(BaseModel):
    """Базовая конфигурация шлюза."""

    model_config = ConfigDict(from_attributes=True, extra='allow')

    id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('id', 'gateway_id')
    )
    name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('name', 'gateway_name')
    )
    storage: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('storage', 'storage_type', 'db_type')
    )


class RegistryConfig(BaseModel):
    """Конфигурация регистра устройств."""

    model_config = ConfigDict(from_attributes=True, extra='allow')

    max_devices: Optional[int] = Field(
        default=None,
        gt=0,
        validation_alias=AliasChoices('max_devices', 'max')
    )
    timeout_stale: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices('timeout_stale', 'stale')
    )
    check_interval: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices('check_interval', 'heartbeat')
    )


class MessageBusConfig(BaseModel):
    """Конфигурация шины сообщений."""

    model_config = ConfigDict(from_attributes=True, extra='allow')
    max_queue: Optional[int] = Field(
        default=None,
        gt=0,
        validation_alias=AliasChoices('max_queue', 'max_size')
    )
    timeout: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices('timeout', 'cooldown')
    )


class LoggerConfig(BaseModel):
    """Конфигурация логирования."""

    model_config = ConfigDict(from_attributes=True, extra='allow')
    dir: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('dir', 'logdir')
    )
    debug: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices('debug', 'debug_mode')
    )
    level: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('level', 'loglevel')
    )


class BaseAdapterConfig(BaseModel):
    """Базовая конфигурация адаптера."""

    model_config = ConfigDict(from_attributes=True, extra='allow')
    enabled: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices('enabled', 'on')
    )
    timeout_reject: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices('timeout_reject', 'ttl')
    )


class AdapterConfig(BaseAdapterConfig):
    """
    Обычная конфигурация адаптера.

    Отличается от Base, так как часть этих атрибутов
    не используется у MQTT.
    """

    host: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('host', 'address')
    )
    port: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices('port')
    )
    url_root: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('url_root', 'root', 'url_base', 'url')
    )
    endpoints: Optional[dict] = Field(
        default=None,
        validation_alias=AliasChoices('endpoints', 'urls')
    )


class WebSocketConfig(AdapterConfig):
    """Конфигурация WebSocket-адаптера."""

    heartbeat: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices('heartbeat', 'conn_check_interval')
    )


class SubscriptionConfig(BaseModel):
    """Подписка MQTT."""

    topic: str = Field(
        default='',
        validation_alias=AliasChoices('topic', 'name', 'link', 'url')
    )
    qos: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices('qos')
    )


class MQTTConfig(BaseAdapterConfig):
    """Конфигурация MQTT-адаптера."""

    client_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('client_id', 'id')
    )

    class Broker(BaseModel):
        """MQTT-брокер."""

        host: Optional[str] = Field(
            default=None,
            validation_alias=AliasChoices('host', 'broker_host')
        )
        port: Optional[int] = Field(
            default=None,
            validation_alias=AliasChoices('port', 'broker_port')
        )

    broker: Optional[Broker] = Field(
        default=None,
        validation_alias=AliasChoices('broker')
    )

    version: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            'version',
            'protocol_version',
            'mqtt_version'
        )
    )
    keepalive: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices('keepalive')
    )
    qos: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices('qos')
    )
    reconnect_delay: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices(
            'reconnect_delay',
            'default_reconnect_delay'
        )
    )
    max_reconnect_delay: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices('max_reconnect_delay')
    )
    subscriptions: Optional[dict[str, SubscriptionConfig]] = Field(
        default=None,
        validation_alias=AliasChoices('subscriptions', 'topics')
    )


AdapterConfigType = Union[
    BaseAdapterConfig | AdapterConfig | WebSocketConfig | MQTTConfig
]


def _create_adapter_config(
    key: str,
    data: Dict[str, Any]
) -> AdapterConfigType:
    """Фабрика для создания конфигурации адаптера по имени протокола."""
    adapter_mapping = {
        'mqtt': MQTTConfig,
        'websocket': WebSocketConfig,
    }
    adapter_class = adapter_mapping.get(key, AdapterConfig)
    return adapter_class(**data)


class MainGatewayConfig(BaseModel):
    """
    Основная часть конфигурации шлюза.

    Сюда входит та конфигурация, которая начинается с GATEWAY__.
    """

    model_config = ConfigDict(from_attributes=True, extra='allow')

    general: Optional[GeneralGatewayConfig] = Field(
        default=None,
        validation_alias=AliasChoices('gateway', 'general')
    )
    devices: Optional[RegistryConfig] = Field(
        default=None,
        validation_alias=AliasChoices('registry', 'devices')
    )
    bus: Optional[MessageBusConfig] = Field(
        default=None,
        validation_alias=AliasChoices('message_bus', 'bus')
    )
    logger: Optional[LoggerConfig] = Field(
        default=None,
        validation_alias=AliasChoices('logger', 'logging', 'logs')
    )


class GatewayConfig(BaseModel):
    """Публичная часть конфигурации шлюза."""

    model_config = ConfigDict(from_attributes=True, extra='allow')

    general_config: Optional[MainGatewayConfig] = Field(
        default=None,
        validation_alias=AliasChoices('gateway', 'main')
    )

    adapter_configs: Optional[dict[str, AdapterConfigType]] = Field(
        default=None,
        validation_alias=AliasChoices('adapters', 'protocols')
    )

    @field_validator('adapter_configs', mode='before')
    @classmethod
    def validate_adapter_configs(
        cls,
        v: Optional[dict[str, Any]]
    ) -> Dict[str, AdapterConfigType]:
        """Валидация поля adapter_config."""
        if v is None:
            return {}
        result = {}
        for key, val in v.items():
            try:
                res = _create_adapter_config(key.lower(), val)
            except ValidationError as ve:
                logger.exception(
                    f"Ошибка валидации для конфигурации адаптера '{key}': {ve}"
                )
                res = BaseAdapterConfig(enabled=False)
            except Exception as ex:
                logger.exception(
                    f"Ошибка для конфигурации адаптера '{key}': {ex}"
                )
                res = BaseAdapterConfig(enabled=False)
            result[key] = res
        return result
