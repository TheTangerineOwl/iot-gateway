"""Модуль сообщения."""
from dataclasses import dataclass, field
from enum import Enum
import logging
from time import time
from typing import Any
from uuid import uuid4
from .device import ProtocolType


logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Тип сообщения в системе."""

    TELEMETRY = "telemetry"
    COMMAND = "command"
    COMMAND_RESPONSE = "command_response"
    EVENT = "event"
    STATUS = "status"
    REGISTRATION = "register"
    HEARTBEAT = "heartbeat"


@dataclass
class Message:
    """Сообщение с устройства."""

    message_id: str = field(default_factory=lambda: str(uuid4()))
    message_type: MessageType = MessageType.TELEMETRY
    message_topic: str = ''
    device_id: str = ''
    protocol: ProtocolType = ProtocolType.UNKNOWN
    schema_version: str = '1.0'
    metadata: dict[str, Any] = field(default_factory=dict)
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
            'payload': self.payload,
            'timestamp': self.timestamp,
            'processed': self.processed,
            'protocol': self.protocol,
            'schema_version': self.schema_version,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, json: dict[str, Any]) -> "Message":
        """Получить сообщение из словаря."""
        return cls(
            message_id=str(
                json.get('message_id', str(uuid4()))
            ),
            message_type=MessageType(
                str(json.get('message_type', MessageType.TELEMETRY))
            ),
            message_topic=str(
                json.get('message_topic', '')
            ),
            device_id=str(
                json.get('device_id', '')
            ),
            protocol=ProtocolType(
                str(json.get('protocol', ProtocolType.UNKNOWN))
            ),
            payload=dict(
                json.get('payload', dict())
            ),
            timestamp=float(
                json.get('timestamp', time())
            ),
            schema_version=str(
                json.get('schema_version', '1.0')
            ),
            metadata=dict(
                json.get('metadata', dict())
            )
        )
