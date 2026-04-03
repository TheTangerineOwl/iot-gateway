"""Подписчик шины сообщений для сохранения телеметрии в хранилище."""
import logging
from models.message import Message
from models.telemetry import TelemetryRecord
from storage.base import StorageBase

logger = logging.getLogger(__name__)


class StorageSubscriber:
    """
    Подписчик шины сообщений для хранилища.

    Сохраняет обработанную телеметрию в хранилище.
    """

    def __init__(self, storage: StorageBase) -> None:
        """Инициализировать подписчика с заданным хранилищем."""
        self._storage = storage

    async def handle(self, message: Message) -> None:
        """Обработать сообщение из шины и сохранить запись телеметрии."""
        try:
            record = TelemetryRecord.from_message(message)
            await self._storage.save(record)
        except Exception as exc:
            logger.exception(
                "Storage error for message %s: %s",
                message.message_id, exc
            )
