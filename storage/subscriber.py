"""Подписчик шины сообщений для сохранения телеметрии в хранилище."""
import logging
from models.device import Device, DeviceStatus
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
            if not message.processed:
                raise ValueError(
                    'trying to save unproccesed message to storage'
                )
            record = TelemetryRecord.from_message(message)
            await self._storage.save(record)
        except Exception as exc:
            logger.exception(
                "Storage error for message %s: %s",
                message.message_id, exc
            )

    async def on_device_register(self, device: Device) -> None:
        """Колбэк регистра: сохранить/обновить устройство в БД."""
        try:
            await self._storage.upsert_device(device)
            logger.debug("Device persisted: %s", device.device_id)
        except Exception as exc:
            logger.exception(
                "Storage error on device register %s: %s",
                device.device_id, exc
            )

    async def on_device_status_update(
            self,
            device: Device,
            old_status: DeviceStatus,
            new_status: DeviceStatus
    ) -> None:
        """Колбэк регистра: обновить статус устройства в БД."""
        try:
            if old_status == new_status:
                logger.debug(
                    "Device status not changed: "
                    "new is the same status"
                )
            await self._storage.upsert_device(device)
            logger.debug("Device status changed: %s", device.device_id)
        except Exception as exc:
            logger.exception(
                "Storage error on device register %s: %s",
                device.device_id, exc
            )

    async def on_device_unregister(self, device: Device) -> None:
        """Колбэк регистра: удалить устройство из БД при дерегистрации."""
        try:
            await self._storage.delete_device(device.device_id)
            logger.debug("Device removed from storage: %s", device.device_id)
        except Exception as exc:
            logger.exception(
                "Storage error on device unregister %s: %s",
                device.device_id, exc
            )
