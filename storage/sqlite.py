"""Хранилище телеметрии на базе SQLite."""
import aiosqlite
import json
import logging
import os
from storage.base import StorageBase
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

STATEMENTS = [
    CREATE_TABLE,
    CREATE_IDX_DEVICE,
    CREATE_IDX_TS,
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
                message_id=row[0],
                device_id=row[1],
                protocol=row[2],
                payload=json.loads(row[3]),
                timestamp=row[4],
            )
            for row in rows
        ]
