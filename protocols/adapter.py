from abc import ABC, abstractmethod
from models.message import Message
from core.message_bus import MessageBus
from core.registry import DeviceRegistry
from typing import Any


class ProtocolAdapter(ABC):
    def __init__(self) -> None:
        self.bus: MessageBus | None = None
        self.registry: DeviceRegistry | None = None
        self.running = False

    @property
    @abstractmethod
    def protocol_name(self):
        pass

    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    async def stop(self):
        pass

    @property
    def is_running(self):
        return self.is_running

    def set_gateway_context(
            self,
            message_bus: MessageBus,
            registry: DeviceRegistry
    ):
        self.bus = message_bus
        self.registry = registry

    async def publish_message(self, message_type: str, message: Message):
        if not self.bus:
            raise RuntimeError(
                f'Adapter {self.protocol_name} not connected to message bus.'
            )
        message.protocol = self.protocol_name
        await self.bus.publish(message_type, message)

    # async def send_command(
    #         self,
    #         device_id: str,
    #         commands: str,
    #         params: dict[str, Any] | None = None
    # ):
    #     pass

    async def health_check(self):
        return {
            'protocol': self.protocol_name,
            'running': self.running
        }
