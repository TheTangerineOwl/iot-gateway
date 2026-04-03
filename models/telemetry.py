"""Модель записи телеметрии для хранилища."""
from dataclasses import dataclass, field
from time import time
from typing import Any


@dataclass
class TelemetryRecord:
    """Запись телеметрии для хранилища."""

    device_id: str
    payload: dict[str, Any]
    timestamp: float = field(default_factory=time)
    message_id: str = ''
    protocol: str = ''

    @classmethod
    def from_message(cls, message) -> 'TelemetryRecord':
        """Создать запись из объекта Message."""
        return cls(
            device_id=message.device_id,
            payload=message.payload,
            timestamp=message.timestamp,
            message_id=message.message_id,
            protocol=message.protocol,
        )
