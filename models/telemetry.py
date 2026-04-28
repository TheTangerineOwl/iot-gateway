"""Модель записи телеметрии для хранилища."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from models.device import ProtocolType


@dataclass
class TelemetryRecord:
    """Запись телеметрии для хранилища."""

    device_id: str
    payload: dict[str, Any]
    timestamp: float = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).timestamp()
    )
    message_id: str = ''
    protocol: ProtocolType = ProtocolType.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        """Создать словарь из записи."""
        return {
            'device_id': self.device_id,
            'payload': self.payload,
            'timestamp': self.timestamp,
            'message_id': self.message_id,
            'protocol': self.protocol.value
        }

    @classmethod
    def from_dict(cls, dic: dict[str, Any]) -> 'TelemetryRecord':
        """Создать запись из словаря."""
        if 'device_id' not in dic.keys():
            raise ValueError('device_id is required')
        if 'payload' not in dic.keys():
            raise ValueError('empty payload')
        return cls(
            device_id=str(dic.get('device_id', '')),
            payload=dic.get('payload', {}),
            timestamp=float(dic.get(
                'timestamp', datetime.now(tz=timezone.utc).timestamp())
            ),
            message_id=str(dic.get('message_id', '')),
            protocol=ProtocolType(dic.get('protocol', ProtocolType.UNKNOWN))
        )

    @classmethod
    def from_message(cls, message) -> 'TelemetryRecord':
        """Создать запись из объекта Message."""
        return cls(
            device_id=message.device_id,
            payload=message.payload,
            timestamp=message.timestamp,
            message_id=message.message_id,
            protocol=message.protocol
        )
