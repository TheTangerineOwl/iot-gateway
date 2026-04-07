"""Модуль сообщения."""
from dataclasses import dataclass, field
from enum import Enum
import logging
from time import time
from typing import Any
from uuid import uuid4


logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Тип сообщения в системе."""

    TELEMETRY = "telemetry"
    COMMAND = "command"
    COMMAND_RESPONSE = "command_response"
    EVENT = "event"
    STATUS = "status"
    REGISTRATION = "registration"
    HEARTBEAT = "heartbeat"


@dataclass
class Message:
    """Сообщение с устройства."""

    message_id: str = field(default_factory=lambda: str(uuid4()))
    message_type: MessageType = MessageType.TELEMETRY
    message_topic: str = ''
    device_id: str = ''
    protocol: str = ''
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time)
    processed: bool = field(default=False, init=False)

    def to_dict(self) -> dict[str, Any]:
        """Получить данные сообщения."""
        return {
            'message_id': self.message_id,
            'message_type': self.message_type.value,
            'message_topic': self.message_topic,
            'device_id': self.device_id,
            'protocol': self.protocol,
            'payload': self.payload,
            'timestamp': self.timestamp,
            'processed': self.processed
        }

    @classmethod
    def from_dict(cls, json: dict[str, Any]) -> "Message":
        return cls(
            message_id=json.get('message_id', str(uuid4())),
            message_type=json.get('message_type', MessageType.TELEMETRY),
            message_topic=json.get('message_topic', ''),
            device_id=json.get('device_id', ''),
            protocol=json.get('protocol', ''),
            payload=json.get('payload', dict()),
            timestamp=json.get('timestamp', time())
        )
