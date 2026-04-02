"""Этапы обработки сообщения на конвейере."""
from abc import ABC, abstractmethod
import logging
from models.message import Message


logger = logging.getLogger(__name__)


class PipelineStage(ABC):
    """Абстрактный класс для этапа конвейера."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Абстрактное свойство для вывода имени этапа."""
        pass

    @abstractmethod
    async def process(self, message: Message) -> Message | None:
        """Абстрактный метод для обработки сообщения на этапе."""
        pass

    async def setup(self) -> None:
        """Инициализация этапа (вызывается при старте pipeline)."""
        pass

    async def teardown(self) -> None:
        """Деинициализация этапа."""
        pass


class ValidationStage(PipelineStage):
    """Этап простой валидации сообщения."""

    @property
    def name(self) -> str:
        """Имя этапа."""
        return "validation"

    async def process(self, message: Message) -> Message | None:
        """Валидация сообщения."""
        if not message.device_id:
            logger.info("Message discarded: no device_id")
            return None
        if not message.payload:
            logger.info(
                "Message discarded: empty payload from %d", message.device_id
            )
            return None
        return message
