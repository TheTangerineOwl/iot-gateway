"""Абстрактный интерфейс хранилища данных."""
from abc import ABC, abstractmethod
from models.telemetry import TelemetryRecord
from models.device import Device


class StorageBase(ABC):
    """Базовый класс хранилища телеметрии."""

    @abstractmethod
    async def setup(self) -> None:
        """Инициализировать соединение и схему БД."""
        pass

    @abstractmethod
    async def teardown(self) -> None:
        """Закрыть соединение с БД."""
        pass

    @abstractmethod
    async def save(self, record: TelemetryRecord) -> None:
        """Сохранить запись телеметрии."""
        pass

    @abstractmethod
    async def upsert_device(self, device: Device) -> None:
        """Сохранить или обновить устройство в БД."""
        pass

    @abstractmethod
    async def delete_device(self, device_id: str) -> None:
        """Удалить устройство из БД."""
        pass

    @abstractmethod
    async def load_devices(self) -> list[Device]:
        """Загрузить все устройства из БД."""
        pass

    @abstractmethod
    async def get_by_device(
        self,
        device_id: str,
        limit: int = 100
    ) -> list[TelemetryRecord]:
        """Получить последние записи по устройству."""
        pass
