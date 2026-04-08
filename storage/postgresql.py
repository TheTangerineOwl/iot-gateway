"""Хранилище телеметрии на базе PostgreSQL."""
from contextlib import contextmanager
import psycopg
from psycopg.connection_async import AsyncConnection
from psycopg.rows import RowFactory
import json
import logging
from storage.base import (
    CREATE_TABLE, INSERT_SQL, SELECT_BY_DEVICE, StorageBase
)
from models.telemetry import TelemetryRecord


logger = logging.getLogger(__name__)


class PostgresStorage(StorageBase):
    """Хранилище телеметрии на PostgreSQL."""

    _conn: AsyncConnection | None = None

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
            row_factory=RowFactory
        )
        try:
            yield self._conn
        finally:
            await self._conn.close()

    async def setup(self) -> None:
        """Открыть БД и создать таблицу."""
        try:
            self._conn = await AsyncConnection.connect(
                conninfo=self._conn_str
            )
            if self._conn is None:
                raise psycopg.DatabaseError('Connection not established')
            async with self._conn.cursor(row_factory=RowFactory) as cur:
                await cur.execute(CREATE_TABLE)
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

    async def save(self, record: TelemetryRecord) -> None:
        """Сохранить запись телеметрии."""
        if self._conn is None:
            raise psycopg.DatabaseError('Connection not established')
        async with self._conn.cursor(row_factory=RowFactory) as cur:
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
        async with self._conn.cursor(row_factory=RowFactory) as cur:
            await cur.execute(sql, (device_id, limit))
            await self._conn.commit()
            rows = await cur.fetchall()

        return [
            TelemetryRecord(
                message_id=row['message_id'],
                device_id=row['device_id'],
                protocol=row['protocol'],
                payload=json.loads(row['payload']),
                timestamp=row['timestamp'],
            )
            for row in rows
        ]
