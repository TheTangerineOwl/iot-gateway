from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Any
from uuid import uuid4


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
    processed: bool = False
    value: Any = ''
