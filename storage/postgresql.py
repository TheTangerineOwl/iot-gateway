"""Хранилище телеметрии на базе PostgreSQL."""
import asyncio
from contextlib import contextmanager
import psycopg
from psycopg.connection_async import AsyncConnection
from psycopg.rows import dict_row
import json
import logging
from typing import Any
from storage.base import StorageBase
from models.device import ProtocolType, Device
from models.telemetry import TelemetryRecord


logger = logging.getLogger(__name__)


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS telemetry (
    id         BIGSERIAL       PRIMARY KEY,
    message_id TEXT            NOT NULL,
    device_id  TEXT            NOT NULL,
    protocol   TEXT            DEFAULT '',
    payload    TEXT            NOT NULL,
    timestamp  DOUBLE PRECISION NOT NULL
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
    name           TEXT             NOT NULL DEFAULT '',
    device_type    TEXT             NOT NULL DEFAULT 'unknown',
    device_status  TEXT             NOT NULL DEFAULT 'offline',
    protocol       TEXT             NOT NULL DEFAULT 'Unknown',
    last_response  DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at     DOUBLE PRECISION NOT NULL DEFAULT 0.0
);
"""

STATEMENTS = [
    CREATE_TABLE,
    CREATE_IDX_DEVICE,
    CREATE_IDX_TS,
    CREATE_DEVICES_TABLE
]

INSERT_SQL = """
INSERT INTO telemetry
    (message_id, device_id, protocol, payload, timestamp)
VALUES (%s, %s, %s, %s, %s);
"""

SELECT_BY_DEVICE = """
    SELECT message_id, device_id, protocol, payload, timestamp
    FROM telemetry
    WHERE device_id = %s
    ORDER BY timestamp DESC
    LIMIT %s;
"""

UPSERT_DEVICE_SQL = """
INSERT INTO devices
    (device_id, name, device_type, device_status,
     protocol, last_response, created_at)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT(device_id) DO UPDATE SET
    name          = EXCLUDED.name,
    device_type   = EXCLUDED.device_type,
    device_status = EXCLUDED.device_status,
    protocol      = EXCLUDED.protocol,
    last_response = EXCLUDED.last_response;
"""

DELETE_DEVICE_SQL = """
DELETE FROM devices WHERE device_id = %s;
"""

SELECT_ALL_DEVICES = """
SELECT device_id, name, device_type, device_status,
 protocol, last_response, created_at
FROM devices;
"""


class PostgresStorage(StorageBase):
    """Хранилище телеметрии на PostgreSQL."""

    _conn: AsyncConnection[dict[str, Any]] | None = None

    def __init__(
        self,
        connstr: str
    ) -> None:
        """Хранилище телеметрии на базе PostgreSQL."""
        self._conn_str = connstr

    @contextmanager
    async def get_db_connection(self):
        """Менеджер контекста для PostgreSQL подключения."""
        self._conn = await AsyncConnection.connect(
            conninfo=self._conn_str,
            row_factory=dict_row
        )
        try:
            yield self._conn
        finally:
            await self._conn.close()

    async def setup(self) -> None:
        """Открыть БД и создать таблицу."""
        try:
            self._conn = await AsyncConnection.connect(
                conninfo=self._conn_str,
                row_factory=dict_row
            )
            if self._conn is None:
                raise psycopg.DatabaseError('Connection not established')
            async with self._conn.cursor() as cur:
                for statement in STATEMENTS:
                    await cur.execute(statement)
            await self._conn.commit()
            logger.info("PostgresStorage ready")
        except Exception as exc:
            logger.exception(
                "Coudn't setup PostgreSQL storage: %s", exc
            )

    async def teardown(self) -> None:
        """Закрыть соединение."""
        if self._conn is None:
            raise psycopg.DatabaseError('Connection not established')
        await self._conn.close()
        self._conn = None
        logger.info("PostgresStorage closed")
        await asyncio.sleep(0)

    async def save(self, record: TelemetryRecord) -> None:
        """Сохранить запись телеметрии."""
        if self._conn is None:
            raise psycopg.DatabaseError('Connection not established')
        async with self._conn.cursor() as cur:
            await cur.execute(
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
            raise psycopg.DatabaseError('Connection not established')
        async with self._conn.cursor() as cur:
            await cur.execute(sql, (device_id, limit))
            # await self._conn.commit()
            rows = await cur.fetchall()

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
        """Обновить или создать устройство в БД."""
        if self._conn is None:
            raise psycopg.DatabaseError('Connection not established')
        async with self._conn.cursor() as cur:
            await cur.execute(
                UPSERT_DEVICE_SQL,
                (
                    device.device_id,
                    device.name,
                    device.device_type.value,
                    device.device_status.value,
                    device.protocol.value,
                    device.last_response,
                    device.created_at,
                ),
            )
        await self._conn.commit()

    async def delete_device(self, device_id: str) -> None:
        """Удалить устройство из БД."""
        if self._conn is None:
            raise psycopg.DatabaseError('Connection not established')
        async with self._conn.cursor() as cur:
            await cur.execute(
                DELETE_DEVICE_SQL,
                (device_id,)
            )
        await self._conn.commit()

    async def load_devices(self) -> list[Device]:
        """Загрузить устройства из БД."""
        if self._conn is None:
            raise psycopg.DatabaseError('Connection not established')
        async with self._conn.cursor() as cur:
            await cur.execute(SELECT_ALL_DEVICES)
            rows = await cur.fetchall()
        return [Device.from_dict(row) for row in rows]
