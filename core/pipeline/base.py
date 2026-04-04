"""Абстрактные классы для конвейера."""
from abc import ABC, abstractmethod
from models.message import Message


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
