"""Абстрактный интерфейс хранилища данных."""
from abc import ABC, abstractmethod
from models.telemetry import TelemetryRecord


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS telemetry (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT    NOT NULL,
    device_id  TEXT    NOT NULL,
    protocol   TEXT    DEFAULT '',
    payload    TEXT    NOT NULL,
    timestamp  REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_device_id
    ON telemetry (device_id);
CREATE INDEX IF NOT EXISTS idx_timestamp
    ON telemetry (timestamp);
"""

INSERT_SQL = """
INSERT INTO telemetry
    (message_id, device_id, protocol, payload, timestamp)
VALUES (?, ?, ?, ?, ?);
"""


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
    async def get_by_device(
        self,
        device_id: str,
        limit: int = 100
    ) -> list[TelemetryRecord]:
        """Получить последние записи по устройству."""
        pass
