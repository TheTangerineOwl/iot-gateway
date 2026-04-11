"""Модуль девайса."""
from dataclasses import dataclass, field
from enum import Enum
import logging
from time import time
from typing import Any
import uuid


logger = logging.getLogger(__name__)


class DeviceStatus(str, Enum):
    """Текущий статус устройства."""

    ONLINE = 'online'
    OFFLINE = 'offline'
    ERROR = 'error'
    PAIRING = 'pairing'
    SLEEPING = 'sleeping'


class DeviceType(str, Enum):
    """Тип устройства."""

    SENSOR = 'sensor'
    ACTUATOR = 'actuator'
    CONTROLLER = 'controller'
    GATEWAY = 'gateway'
    UNKNOWN = 'unknown'


class ProtocolType(str, Enum):
    """Тип протокола."""

    HTTP = 'http'
    MQTT = 'mqtt'
    WEBSOCKET = 'websocket'
    COAP = 'coap'
    MODBUS = 'modbus'
    UNKNOWN = 'unknown'


@dataclass
class Device:
    """Подключенное устройство."""

    device_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ''
    device_type: DeviceType = DeviceType.UNKNOWN
    device_status: DeviceStatus = DeviceStatus.OFFLINE
    protocol: ProtocolType = ProtocolType.UNKNOWN
    last_response: float = 0.0
    created_at: float = field(default_factory=time)

    def touch(self):
        """Обновляет время последнего обращения."""
        self.last_response = time()

    def is_stale(self, timeout: float = 300.0):
        """Проверяет, отвечает ли устройство."""
        if self.last_response == 0.0:
            return True
        return (time() - self.last_response) > timeout

    def to_dict(self) -> dict[str, Any]:
        """Вывод информации о девайсе."""
        return {
            "device_id": self.device_id,
            "name": self.name,
            "device_type": self.device_type.value,
            "protocol": self.protocol.value,
            "device_status": self.device_status.value,
            "last_response": self.last_response,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Device":
        """Преобразовать данные сообщения в девайс."""
        return cls(
            device_id=str(
                data.get("device_id", uuid.uuid4())
            ),
            name=str(
                data.get("name", "")
            ),
            device_type=DeviceType(
                str(data.get("device_type", "unknown")).lower()
            ),
            protocol=ProtocolType(
                str(data.get("protocol", "unknown")).lower()
            ),
            device_status=DeviceStatus(
                str(data.get("device_status", "offline")).lower()
            ),
            last_response=float(
                data.get("last_response", 0.0)
            ),
            created_at=float(
                data.get("created_at", time())
            ),
        )
