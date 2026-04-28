"""Абстрактные классы для адаптеров."""
from abc import ABC, abstractmethod
import asyncio
import logging
from typing import Any
from config.config import YAMLConfigLoader
from config.topics import TopicKey, TopicManager
from models.message import Message, MessageType
from models.device import ProtocolType
from core.message_bus import MessageBus
from core.registry import DeviceRegistry


logger = logging.getLogger(__name__)


class ProtocolAdapter(ABC):
    """Абстрактный класс для адаптеров протоколов."""

    def __init__(self, config: YAMLConfigLoader) -> None:
        """Конструктор адаптера."""
        self._config: YAMLConfigLoader = config
        self._bus: MessageBus | None = None
        self._topics: TopicManager | None = None
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
        self._topics = self._bus.topics
        self._registry = registry

    def get_topic(
        self,
        key: TopicKey | str,
        default: Any | None = None,
        **kwargs: str
    ) -> str:
        """Возвращает стандартный топик."""
        if self._topics is None:
            raise RuntimeError('Topics for adapter are not set')
        return self._topics.get(
            key, default, **kwargs
        )

    def get_sub_pattern(
        self,
        key: TopicKey | str
    ) -> str:
        """Возвращает стандартный топик для подписки."""
        if self._topics is None:
            raise RuntimeError('Topics for adapter are not set')
        return self._topics.get_subscription_pattern(key)

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
        loop = asyncio.get_running_loop()
        # loop = asyncio.get_event_loop()
        fut: asyncio.Future[Message] = loop.create_future()
        self._pending[message.message_id] = fut
        return fut

    async def _handle_rejected_base(self, message: Message) -> None:
        fut = self._pending.pop(message.message_id, None)
        if fut and not fut.done():
            fut.set_result(message)

    async def _handle_command_response(
        self,
        device_id: str,
        payload: dict[str, Any]
    ) -> None:
        """Принять ответ устройства и опубликовать на шину."""
        message = Message(
            message_type=MessageType.COMMAND_RESPONSE,
            device_id=device_id,
            protocol=self.protocol_type,
            payload=payload,
            message_topic=self.get_topic(
                TopicKey.DEVICES_COMMAND_RESPONSE,
                device_id=device_id
            )
        )
        await self._publish_message(message.message_topic, message)
        logger.info(
            f'Command response from device {device_id}: {payload}'
        )

    @abstractmethod
    async def send_command(
        self,
        device_id: str,
        command: str,
        params: dict[str, Any] | None = None,
    ) -> bool:
        """
        Отправить команду на устройство.

        Args:
            device_id: идентификатор устройства.
            command:   имя команды (например, "reboot", "set_interval").
            params:    произвольные параметры команды.

        Returns:
            True  — команда доставлена (или поставлена в очередь).
            False — адаптер не может доставить команду прямо сейчас.
        """
        return False

    async def _health_check(self) -> dict[str, Any]:
        """Вернуть состояние адаптера."""
        return {
            'protocol': self.protocol_name,
            'running': self._running
        }
