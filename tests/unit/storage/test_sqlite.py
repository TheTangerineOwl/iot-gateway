"""Тест хранилища SQLite."""
import pytest
import pytest_asyncio
import aiosqlite
from json import loads
from unittest.mock import AsyncMock
from storage.sqlite import SQLiteStorage, SELECT_BY_DEVICE
from models.telemetry import TelemetryRecord
from tests.conftest import not_raises


@pytest_asyncio.fixture
async def storage(tmp_path):
    """Тестовое подключение к БД."""
    db = SQLiteStorage(db_path=str(tmp_path / "test.db"))
    await db.setup()
    yield db
    await db.teardown()


class TestSQLiteStorage:
    """Тесты для хранилища SQLite."""

    class TestSetup:
        """Тесты для setup."""

        @pytest.mark.asyncio
        async def test_setup_creates_db_file(
            self,
            tmp_path
        ):
            """setup() создаёт файл базы данных на диске."""
            db_path = tmp_path / "subdir" / "test.db"
            db = SQLiteStorage(db_path=str(db_path))
            await db.setup()
            try:
                assert db_path.exists()
            finally:
                await db.teardown()

        @pytest.mark.asyncio
        async def test_setup_connection_not_none(
            self,
            tmp_path
        ):
            """После setup() соединение установлено."""
            db = SQLiteStorage(db_path=str(tmp_path / "test.db"))
            await db.setup()
            try:
                assert db._conn is not None
            finally:
                await db.teardown()

    class TestTeardown:
        """Тесты teardown()."""

        @pytest.mark.asyncio
        async def test_teardown_closes_connection(
            self,
            mock_conn: AsyncMock,
            tmp_path
        ):
            """При остановке хранилища закрывается соединение."""
            storage = SQLiteStorage(db_path=str(tmp_path / "test.db"))
            await storage.setup()

            storage._conn = mock_conn
            with not_raises(Exception):
                await storage.teardown()

            mock_conn.close.assert_awaited_once()
            assert storage._conn is None

        @pytest.mark.asyncio
        async def test_teardown_wo_setup_raises(
            self,
            tmp_path
        ):
            """Остановка без старта вызывает исключение."""
            storage = SQLiteStorage(db_path=str(tmp_path / 'test.db'))
            with pytest.raises(
                aiosqlite.DatabaseError,
                match='Connection not established'
            ):
                await storage.teardown()

    class TestSave:
        """Тесты save."""

        @pytest.mark.asyncio
        async def test_save_get(
            self,
            record: TelemetryRecord,
            storage: SQLiteStorage
        ):
            """Сообщение должно сохраняться в БД."""
            await storage.save(record)

            results = await storage.get_by_device(record.device_id)

            assert len(results) == 1
            assert results[0] == record

        @pytest.mark.asyncio
        async def test_save_wo_connection(
            self
        ):
            """Если подключение не установлено, то исключение."""
            storage = SQLiteStorage(db_path='irrelevant.db')
            record = TelemetryRecord(device_id="x", payload={})

            with pytest.raises(
                aiosqlite.DatabaseError,
                match='Connection not established'
            ):
                await storage.save(record)

        @pytest.mark.asyncio
        async def test_save_payload_serialized_as_json(
            self,
            storage: SQLiteStorage,
            record: TelemetryRecord
        ):
            """save() сохраняет payload как JSON-строку, не как dict."""
            await storage.save(record)

            assert storage._conn is not None
            async with storage._conn.execute(
                SELECT_BY_DEVICE, (record.device_id, 1)
            ) as cur:
                row = await cur.fetchone()

            assert row is not None
            assert 'payload' in row.keys()
            raw = row["payload"]
            assert isinstance(raw, str)
            assert loads(raw) == record.payload

        @pytest.mark.asyncio
        async def test_multiple_saves_all_returned(
            self,
            storage: SQLiteStorage,
            record: TelemetryRecord
        ):
            """Возвращаются все сохраненные записи."""
            record2 = record
            record2.message_id = 'mes-002'
            await storage.save(record)
            await storage.save(record2)

            results = await storage.get_by_device(record.device_id)
            assert len(results) == 2

    class TestGetByDevice:
        """Тест get_by_device."""

        @pytest.mark.asyncio
        async def test_get_by_device_empty_if_unknown(
            self,
            storage: SQLiteStorage
        ):
            """Если девайс неизвестен, то возврат пустой."""
            results = await storage.get_by_device("unknown-device")
            assert results == []

        @pytest.mark.asyncio
        async def test_get_by_device_passes_limit(
            self,
            storage: SQLiteStorage,
            record: TelemetryRecord
        ):
            """get_by_device() уважает параметр limit."""
            for i in range(5):
                r = record
                r.message_id = f'mes-00{i}'
                await storage.save(r)

            results = await storage.get_by_device(record.device_id, limit=3)
            assert len(results) == 3

        @pytest.mark.asyncio
        async def test_get_by_device_wo_connection_raises(self):
            """get_by_device() без соединения вызывает DatabaseError."""
            db = SQLiteStorage(db_path="irrelevant.db")
            with pytest.raises(
                aiosqlite.DatabaseError,
                match="Connection not established"
            ):
                await db.get_by_device('dev-001')

        @pytest.mark.asyncio
        async def test_get_by_device_payload_deserialized(
            self,
            storage: SQLiteStorage,
            record: TelemetryRecord
        ):
            """get_by_device() возвращает payload как dict, а не строку."""
            await storage.save(record)
            results = await storage.get_by_device(record.device_id)
            assert isinstance(results[0].payload, dict)
            assert results[0].payload == record.payload
