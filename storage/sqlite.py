"""Хранилище телеметрии на базе SQLite."""
import asyncio
import aiosqlite
import json
import logging
import os
from storage.base import StorageBase
from models.device import ProtocolType, Device
from models.telemetry import TelemetryRecord


logger = logging.getLogger(__name__)


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS telemetry (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT            NOT NULL,
    device_id  TEXT            NOT NULL,
    protocol   TEXT            DEFAULT '',
    payload    TEXT            NOT NULL,
    timestamp  REAL            NOT NULL
);
"""

CREATE_IDX_DEVICE = """
CREATE INDEX IF NOT EXISTS idx_device_id
    ON telemetry (device_id);
"""

CREATE_IDX_TS = """
CREATE INDEX IF NOT EXISTS idx_timestamp
    ON telemetry (timestamp);
"""


CREATE_DEVICES_TABLE = """
CREATE TABLE IF NOT EXISTS devices (
    device_id      TEXT PRIMARY KEY,
    name           TEXT    NOT NULL DEFAULT '',
    device_type    TEXT    NOT NULL DEFAULT 'unknown',
    device_status  TEXT    NOT NULL DEFAULT 'offline',
    protocol       TEXT    NOT NULL DEFAULT 'Unknown',
    last_response  REAL    NOT NULL DEFAULT 0.0,
    created_at     REAL    NOT NULL DEFAULT 0.0
);
"""


STATEMENTS = [
    CREATE_TABLE,
    CREATE_IDX_DEVICE,
    CREATE_IDX_TS,
    CREATE_DEVICES_TABLE,
]

INSERT_SQL = """
INSERT INTO telemetry
    (message_id, device_id, protocol, payload, timestamp)
VALUES (?, ?, ?, ?, ?);
"""

SELECT_BY_DEVICE = """
    SELECT message_id, device_id, protocol, payload, timestamp
    FROM telemetry
    WHERE device_id = ?
    ORDER BY timestamp DESC
    LIMIT ?;
"""

UPSERT_DEVICE_SQL = """
INSERT INTO devices
    (device_id, name, device_type, device_status,
     protocol, last_response, created_at)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(device_id) DO UPDATE SET
    name          = excluded.name,
    device_type   = excluded.device_type,
    device_status = excluded.device_status,
    protocol      = excluded.protocol,
    last_response = excluded.last_response;
"""

DELETE_DEVICE_SQL = """
DELETE FROM devices WHERE device_id = ?;
"""

SELECT_ALL_DEVICES = """
SELECT device_id, name, device_type, device_status,
 protocol, last_response, created_at
FROM devices;
"""


class SQLiteStorage(StorageBase):
    """Хранилище телеметрии на SQLite."""

    def __init__(self, db_path: str = "data/telemetry.db") -> None:
        """Хранилище телеметрии на базе SQLte."""
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def setup(self) -> None:
        """Открыть БД и создать таблицу."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        async with self._conn.cursor() as cur:
            for statement in STATEMENTS:
                await cur.execute(statement)
        await self._conn.commit()
        logger.info("SQLiteStorage ready: %s", self._db_path)

    async def teardown(self) -> None:
        """Закрыть соединение."""
        if self._conn is None:
            raise aiosqlite.DatabaseError('Connection not established')
        await self._conn.close()
        self._conn = None
        logger.info("SQLiteStorage closed")
        await asyncio.sleep(0)

    async def save(self, record: TelemetryRecord) -> None:
        """Сохранить запись телеметрии."""
        if self._conn is None:
            raise aiosqlite.DatabaseError('Connection not established')
        await self._conn.execute(
            INSERT_SQL,
            (
                record.message_id,
                record.device_id,
                record.protocol,
                json.dumps(record.payload, ensure_ascii=False),
                record.timestamp,
            ),
        )
        await self._conn.commit()
        logger.log(5, "Saved telemetry from %s", record.device_id)

    async def get_by_device(
        self,
        device_id: str,
        limit: int = 100,
    ) -> list[TelemetryRecord]:
        """Получить последние N записей устройства."""
        sql = SELECT_BY_DEVICE
        if self._conn is None:
            raise aiosqlite.DatabaseError('Connection not established')
        async with self._conn.execute(sql, (device_id, limit)) as cursor:
            rows = await cursor.fetchall()

        return [
            TelemetryRecord(
                message_id=row['message_id'],
                device_id=row['device_id'],
                protocol=ProtocolType(row['protocol']),
                payload=json.loads(row['payload']),
                timestamp=row['timestamp'],
            )
            for row in rows
        ]

    async def upsert_device(self, device: Device) -> None:
        """Обновить или создать девайс в БД."""
        if self._conn is None:
            raise aiosqlite.DatabaseError('Connection not established')
        await self._conn.execute(
            UPSERT_DEVICE_SQL,
            (
                device.device_id,
                device.name,
                device.device_type.value,
                device.device_status.value,
                device.protocol.value,
                device.last_response,
                device.created_at
            ),
        )
        await self._conn.commit()
        logger.debug('Upserted device: %s', device.device_id)

    async def delete_device(self, device_id: str) -> None:
        """Удалить девайс из БД."""
        if self._conn is None:
            raise aiosqlite.DatabaseError('Connection not established')
        await self._conn.execute(DELETE_DEVICE_SQL, (device_id,))
        await self._conn.commit()
        logger.debug("Deleted device: %s", device_id)

    async def load_devices(self) -> list[Device]:
        """Загрузить все девайсы из БД."""
        if self._conn is None:
            raise aiosqlite.DatabaseError('Connection not established')
        async with self._conn.execute(SELECT_ALL_DEVICES) as cursor:
            rows = await cursor.fetchall()
        return [Device.from_dict(dict(row)) for row in rows]
