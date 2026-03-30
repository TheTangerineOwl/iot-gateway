from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Any
import uuid


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
