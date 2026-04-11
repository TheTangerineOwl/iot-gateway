"""Абстрактные классы для адаптеров."""
from abc import ABC, abstractmethod
import asyncio
import logging
from typing import Any
from models.message import Message
from models.device import ProtocolType
from core.message_bus import MessageBus
from core.registry import DeviceRegistry


logger = logging.getLogger(__name__)


class ProtocolAdapter(ABC):
    """Абстрактный класс для адаптеров протоколов."""

    def __init__(self) -> None:
        """Конструктор адаптера."""
        self._bus: MessageBus | None = None
        self._registry: DeviceRegistry | None = None
        self._running = False
        self._pending: dict[str, asyncio.Future[Message]] = {}

    @property
    def protocol_name(self) -> str:
        """Имя протокола."""
        return self.protocol_type.value

    @property
    @abstractmethod
    def protocol_type(self) -> ProtocolType:
        """Тип протокола."""
        return ProtocolType.UNKNOWN

    @abstractmethod
    async def start(self) -> None:
        """Запустить адаптер протокола."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Остановить адаптер протокола."""
        pass

    @property
    def is_running(self) -> bool:
        """Работает ли адаптер."""
        return self._running

    def set_gateway_context(
            self,
            message_bus: MessageBus,
            registry: DeviceRegistry
    ) -> None:
        """Установить контекст работы адаптера."""
        self._bus = message_bus
        self._registry = registry

    async def _publish_message(
        self, message_type: str, message: Message
    ) -> None:
        """Разместить полученное сообщение на шине."""
        if not self._bus:
            raise RuntimeError(
                f'Adapter {self.protocol_name} not connected to message bus.'
            )
        message.protocol = self.protocol_type
        await self._bus.publish(message_type, message)

    def _register_pending(
        self, message: Message
    ) -> asyncio.Future[Message]:
        # loop = asyncio.get_running_loop()
        # fut: asyncio.Future[Message] = loop.create_future()
        fut: asyncio.Future[Message] = asyncio.get_event_loop().create_future()
        self._pending[message.message_id] = fut
        return fut

    async def _handle_rejected_base(self, message: Message) -> None:
        fut = self._pending.pop(message.message_id, None)
        if fut and not fut.done():
            fut.set_result(message)

    # async def send_command(
    #         self,
    #         device_id: str,
    #         commands: str,
    #         params: dict[str, Any] | None = None
    # ):
    #     pass

    async def _health_check(self) -> dict[str, Any]:
        """Вернуть состояние адаптера."""
        return {
            'protocol': self.protocol_name,
            'running': self._running
        }
