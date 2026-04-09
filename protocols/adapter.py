"""Абстрактные классы для адаптеров."""
from abc import ABC, abstractmethod
import logging
from typing import Any
from models.message import Message
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

    @property
    @abstractmethod
    def protocol_name(self) -> str:
        """Имя протокола."""
        pass

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
        message.protocol = self.protocol_name.lower()
        await self._bus.publish(message_type, message)

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
