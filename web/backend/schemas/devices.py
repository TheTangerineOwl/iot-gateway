"""Модели для девайсов."""
from typing import Any, Optional
from pydantic import BaseModel


class Device(BaseModel):
    """Модель устройства."""

    device_id: str
    name: Optional[str] = None
    protocol: Optional[str] = None
    registered_at: Optional[str] = None
    last_seen: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class DeviceList(BaseModel):
    """Модель для списка устройств."""

    devices: list[Device]
    total: int


class CommandRequest(BaseModel):
    """Модель отправляемой команды."""

    command: str
    params: Optional[dict[str, Any]] = None


class CommandResponse(BaseModel):
    """Модель ответа на команду."""

    status: str
    device_id: str
    command: str
