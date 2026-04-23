"""Модели для запросов с и на шлюз."""
from typing import Optional
from pydantic import BaseModel


class AdapterStatus(BaseModel):
    """Модель статуса адаптера протокола."""

    enabled: bool
    healthy: Optional[bool] = None
    port: Optional[int] = None
    broker: Optional[str] = None


class MessageQueueStatus(BaseModel):
    """Модель статуса шины сообщений."""

    size: int
    max_size: int


class GatewayStatus(BaseModel):
    """Модель статуса шлюза."""

    gateway_id: int
    gateway_name: str
    uptime_seconds: Optional[float] = None
    adapters: dict[str, AdapterStatus]
    message_queue: Optional[MessageQueueStatus] = None
    checked_at: str


class GatewayConfig(BaseModel):
    """Модель конфигурации шлюза."""

    gateway_id: int
    gateway_name: str
    http_port: int
    ws_port: int
    coap_port: int
    mqtt_broker: str
    logs_dir: str
