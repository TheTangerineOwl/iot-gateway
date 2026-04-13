"""Тест хранилища PostgreSQL."""
import pytest
import pytest_asyncio
import json
import psycopg
from unittest.mock import AsyncMock, patch
from storage.postgresql import STATEMENTS, INSERT_SQL, PostgresStorage
from models.telemetry import TelemetryRecord


@pytest_asyncio.fixture
async def storage(mock_conn):
    """Тестовое хранилище."""
    with patch(
        'psycopg.connection_async.AsyncConnection.connect',
        return_value=mock_conn
    ):
        db = PostgresStorage(connstr='postgresql://testdb')
        await db.setup()
        yield db


class TestPostgresStorage:
    """Тесты для PostgreSQL хранилища."""

    class TestSetup:
        """Тесты для setup()."""

        @pytest.mark.asyncio
        async def test_setup_create_tb(
            self,
            storage: PostgresStorage,
            mock_conn: AsyncMock,
            mock_cursor: AsyncMock
        ):
            """При запуске хранилища создается подключение и таблица."""
            assert storage._conn is not None
            assert mock_cursor.execute.await_count == len(STATEMENTS)

            actual_calls = [
                call.args[0]
                for call in mock_cursor.execute.call_args_list
            ]

            assert actual_calls == STATEMENTS
            mock_conn.commit.assert_awaited_once()

        @pytest.mark.asyncio
        async def test_setup_exception_is_swallowed(self):
            """Перехватывает исключение при подключении."""
            with patch(
                'psycopg.connection_async.AsyncConnection.connect',
                side_effect=psycopg.OperationalError('refused')
            ):
                db = PostgresStorage(connstr='postgresql://bad')
                await db.setup()
                assert db._conn is None

        @pytest.mark.asyncio
        async def test_setup_after_swallowed_exception_save_raises(
            self,
            record: TelemetryRecord
        ):
            """Если setup не прошел, save выдаст DatabaseError."""
            with patch(
                'psycopg.connection_async.AsyncConnection.connect',
                side_effect=psycopg.OperationalError('refused')
            ):
                db = PostgresStorage(connstr='postgresql://bad')
                await db.setup()

            with pytest.raises(
                psycopg.DatabaseError,
                match='Connection not established'
            ):
                await db.save(record)

    class TestTeardown:
        """Тесты для teardown()."""

        @pytest.mark.asyncio
        async def test_teardown_close_conn(
            self,
            storage: PostgresStorage,
            mock_conn: AsyncMock
        ):
            """При остановке хранилища подключение закрывается."""
            await storage.teardown()
            mock_conn.close.assert_awaited_once()
            assert storage._conn is None

        @pytest.mark.asyncio
        async def test_teardown_wo_setup_raise(self):
            """При остановке хранилища без запуска возникает ошибка."""
            db = PostgresStorage(connstr='postgresql://testdb')
            with pytest.raises(
                psycopg.DatabaseError,
                match='Connection not established'
            ):
                await db.teardown()

    class TestSave:
        """Тесты для save()."""

        @pytest.mark.asyncio
        async def test_save_execute_insert(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock,
            record: TelemetryRecord
        ):
            """При вызове save запись сохраняется с помощью INSERT."""
            await storage.save(record)

            mock_cursor.execute.assert_awaited()
            last_call = mock_cursor.execute.call_args_list[-1]
            sql, params = last_call[0]

            assert sql == INSERT_SQL
            assert params[0] == record.message_id
            assert params[1] == record.device_id
            assert params[2] == record.protocol
            assert json.loads(params[3]) == record.payload
            assert params[4] == record.timestamp

        @pytest.mark.asyncio
        async def test_save_commits(
            self,
            storage: PostgresStorage,
            mock_conn: AsyncMock,
            record: TelemetryRecord
        ):
            """save() должен вызвать commit после INSERT."""
            await storage.save(record)

            # commit вызывался минимум дважды: в setup() и в save()
            assert mock_conn.commit.await_count >= 2

        @pytest.mark.asyncio
        async def test_save_without_connection_raises(
            self,
            record: TelemetryRecord
        ):
            """save() без соединения вызывает DatabaseError."""
            db = PostgresStorage(connstr="postgresql://testdb")
            with pytest.raises(
                psycopg.DatabaseError,
                match="Connection not established"
            ):
                await db.save(record)

        @pytest.mark.asyncio
        async def test_save_payload_serialized_as_json(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock,
            record: TelemetryRecord
        ):
            """Поле payload сериализуется в JSON-строку, не в dict."""
            await storage.save(record)

            last_call = mock_cursor.execute.call_args_list[-1]
            _, params = last_call[0]
            payload_arg = params[3]

            assert isinstance(payload_arg, str)
            assert json.loads(payload_arg) == record.payload

    class TestGetByDevice:
        """Тесты для get_by_device()."""

        @pytest.mark.asyncio
        async def test_get_by_device_empty(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock
        ):
            """get_by_device() возвращает пустой список, если нет записей."""
            mock_cursor.fetchall.return_value = []

            result = await storage.get_by_device("dev-001")

            assert result == []

        @pytest.mark.asyncio
        async def test_get_by_device_returns_records(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock,
            record: TelemetryRecord
        ):
            """get_by_device возвращает список записей с правильными полями."""
            record_dict = record.to_dict()
            record_dict['payload'] = json.dumps(record.payload)
            mock_cursor.fetchall.return_value = [record_dict]

            result = await storage.get_by_device(record.device_id)

            assert len(result) == 1
            assert result[0] == record

        @pytest.mark.asyncio
        async def test_get_by_device_multiple_records(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock,
            record: TelemetryRecord
        ):
            """get_by_device() возвращает все строки из fetchall."""
            records = []
            for i in range(5):
                record.message_id = f'msg-00{i}'
                record_dict = record.to_dict()
                record_dict['payload'] = json.dumps(record.payload)
                records.append(record_dict)
            mock_cursor.fetchall.return_value = records

            result = await storage.get_by_device(record.device_id)
            assert len(result) == 5

        @pytest.mark.asyncio
        async def test_get_by_device_without_connection_raises(self):
            """get_by_device() без соединения вызывает DatabaseError."""
            db = PostgresStorage(connstr="postgresql://testdb")
            with pytest.raises(
                psycopg.DatabaseError,
                match="Connection not established"
            ):
                await db.get_by_device("dev-001")

        @pytest.mark.asyncio
        async def test_get_by_device_passes_limit(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock
        ):
            """get_by_device() передаёт limit вторым параметром в execute."""
            mock_cursor.fetchall.return_value = []

            await storage.get_by_device("dev-001", limit=42)

            last_call = mock_cursor.execute.call_args_list[-1]
            _, params = last_call[0]
            assert params == ("dev-001", 42)

        @pytest.mark.asyncio
        async def test_get_by_device_payload_deserialized(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock,
            record: TelemetryRecord
        ):
            """get_by_device десериализует payload в dict."""
            record_dict = record.to_dict()
            record_dict['payload'] = json.dumps(record.payload)
            mock_cursor.fetchall.return_value = [record_dict]

            result = await storage.get_by_device(record.device_id)

            assert isinstance(result[0].payload, dict)
            assert result[0].payload == record.payload
