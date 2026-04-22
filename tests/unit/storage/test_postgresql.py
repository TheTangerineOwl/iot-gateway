"""Тест хранилища PostgreSQL."""
import pytest
import pytest_asyncio
import json
import psycopg
from unittest.mock import AsyncMock, patch
from storage.postgresql import (
    STATEMENTS,
    INSERT_SQL,
    UPSERT_DEVICE_SQL,
    DELETE_DEVICE_SQL,
    SELECT_ALL_DEVICES,
    CREATE_DEVICES_TABLE,
    PostgresStorage,
)
from models.telemetry import TelemetryRecord
from models.device import Device, DeviceStatus, DeviceType, ProtocolType
from tests.conftest import (
    DEVICE_DEF_ID,
)


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
        async def test_setup_creates_devices_table(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock
        ):
            """CREATE_DEVICES_TABLE присутствует в STATEMENTS и выполняется."""
            assert CREATE_DEVICES_TABLE in STATEMENTS

            actual_calls = [
                c.args[0]
                for c in mock_cursor.execute.call_args_list
            ]
            assert CREATE_DEVICES_TABLE in actual_calls

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
            """get_by_device() передаёт limit в SQL-запрос."""
            mock_cursor.fetchall.return_value = []

            await storage.get_by_device("dev-001", limit=42)

            last_call = mock_cursor.execute.call_args_list[-1]
            _, params = last_call[0]
            assert params[1] == 42

    class TestUpsertDevice:
        """Тесты для upsert_device()."""

        @pytest.mark.asyncio
        async def test_upsert_device_executes_correct_sql(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock,
            device: Device
        ):
            """upsert_device() выполняет UPSERT_DEVICE_SQL."""
            await storage.upsert_device(device)

            last_call = mock_cursor.execute.call_args_list[-1]
            sql, _ = last_call[0]
            assert sql == UPSERT_DEVICE_SQL

        @pytest.mark.asyncio
        async def test_upsert_device_passes_correct_params(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock,
            device: Device
        ):
            """Передаёт все поля устройства в правильном порядке."""
            await storage.upsert_device(device)

            last_call = mock_cursor.execute.call_args_list[-1]
            _, params = last_call[0]

            assert params[0] == device.device_id
            assert params[1] == device.name
            assert params[2] == device.device_type.value
            assert params[3] == device.device_status.value
            assert params[4] == device.protocol.value
            assert params[5] == device.last_response
            assert params[6] == device.created_at

        @pytest.mark.asyncio
        async def test_upsert_device_commits(
            self,
            storage: PostgresStorage,
            mock_conn: AsyncMock,
            device: Device
        ):
            """upsert_device() вызывает commit после выполнения запроса."""
            commit_count_before = mock_conn.commit.await_count
            await storage.upsert_device(device)
            assert mock_conn.commit.await_count == commit_count_before + 1

        @pytest.mark.asyncio
        async def test_upsert_device_without_connection_raises(
            self,
            device: Device
        ):
            """upsert_device() без соединения вызывает DatabaseError."""
            db = PostgresStorage(connstr="postgresql://testdb")
            with pytest.raises(
                psycopg.DatabaseError,
                match="Connection not established"
            ):
                await db.upsert_device(device)

        @pytest.mark.asyncio
        async def test_upsert_device_enum_values_are_strings(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock,
            device: Device
        ):
            """upsert_device() передаёт строковые значения enum, не объекты."""
            await storage.upsert_device(device)

            last_call = mock_cursor.execute.call_args_list[-1]
            _, params = last_call[0]

            assert isinstance(params[2], str)  # device_type
            assert isinstance(params[3], str)  # device_status
            assert isinstance(params[4], str)  # protocol

    class TestDeleteDevice:
        """Тесты для delete_device()."""

        @pytest.mark.asyncio
        async def test_delete_device_executes_correct_sql(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock
        ):
            """delete_device() выполняет DELETE_DEVICE_SQL."""
            await storage.delete_device(DEVICE_DEF_ID)

            last_call = mock_cursor.execute.call_args_list[-1]
            sql, _ = last_call[0]
            assert sql == DELETE_DEVICE_SQL

        @pytest.mark.asyncio
        async def test_delete_device_passes_device_id(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock
        ):
            """delete_device() передаёт device_id в запрос."""
            await storage.delete_device(DEVICE_DEF_ID)

            last_call = mock_cursor.execute.call_args_list[-1]
            _, params = last_call[0]
            assert params[0] == DEVICE_DEF_ID

        @pytest.mark.asyncio
        async def test_delete_device_commits(
            self,
            storage: PostgresStorage,
            mock_conn: AsyncMock
        ):
            """delete_device() вызывает commit после удаления."""
            commit_count_before = mock_conn.commit.await_count
            await storage.delete_device(DEVICE_DEF_ID)
            assert mock_conn.commit.await_count == commit_count_before + 1

        @pytest.mark.asyncio
        async def test_delete_device_without_connection_raises(self):
            """delete_device() без соединения вызывает DatabaseError."""
            db = PostgresStorage(connstr="postgresql://testdb")
            with pytest.raises(
                psycopg.DatabaseError,
                match="Connection not established"
            ):
                await db.delete_device(DEVICE_DEF_ID)

        @pytest.mark.asyncio
        async def test_delete_device_arbitrary_id(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock
        ):
            """delete_device() корректно передаёт произвольный device_id."""
            arbitrary_id = "sensor-xyz-9999"
            await storage.delete_device(arbitrary_id)

            last_call = mock_cursor.execute.call_args_list[-1]
            _, params = last_call[0]
            assert params[0] == arbitrary_id

    class TestLoadDevices:
        """Тесты для load_devices()."""

        @pytest.mark.asyncio
        async def test_load_devices_executes_correct_sql(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock
        ):
            """load_devices() выполняет SELECT_ALL_DEVICES."""
            mock_cursor.fetchall.return_value = []
            await storage.load_devices()

            last_call = mock_cursor.execute.call_args_list[-1]
            sql = last_call[0][0]
            assert sql == SELECT_ALL_DEVICES

        @pytest.mark.asyncio
        async def test_load_devices_returns_empty_list(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock
        ):
            """load_devices() возвращает пустой список, если таблица пуста."""
            mock_cursor.fetchall.return_value = []

            result = await storage.load_devices()

            assert result == []

        @pytest.mark.asyncio
        async def test_load_devices_returns_device_objects(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock,
            device: Device
        ):
            """load_devices() возвращает список объектов Device."""
            mock_cursor.fetchall.return_value = [device.to_dict()]

            result = await storage.load_devices()

            assert len(result) == 1
            assert isinstance(result[0], Device)

        @pytest.mark.asyncio
        async def test_load_devices_maps_fields_correctly(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock,
            device: Device
        ):
            """load_devices() корректно маппит поля строки БД в Device."""
            device_dict = device.to_dict()
            mock_cursor.fetchall.return_value = [device_dict]

            result = await storage.load_devices()

            loaded = result[0]
            assert loaded.device_id == device.device_id
            assert loaded.name == device.name
            assert loaded.device_type == device.device_type
            assert loaded.device_status == device.device_status
            assert loaded.protocol == device.protocol
            assert loaded.last_response == device.last_response
            assert loaded.created_at == device.created_at

        @pytest.mark.asyncio
        async def test_load_devices_multiple_rows(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock,
            device: Device
        ):
            """load_devices() возвращает все устройства из fetchall."""
            devices_data = []
            for i in range(3):
                d = Device(
                    device_id=f"dev-{i:03d}",
                    name=f"Device {i}",
                    device_type=DeviceType.SENSOR,
                    device_status=DeviceStatus.ONLINE,
                    protocol=ProtocolType.HTTP,
                    last_response=float(i),
                    created_at=float(i),
                )
                devices_data.append(d.to_dict())
            mock_cursor.fetchall.return_value = devices_data

            result = await storage.load_devices()

            assert len(result) == 3
            assert all(isinstance(r, Device) for r in result)
            assert [r.device_id for r in result] == [
                "dev-000", "dev-001", "dev-002"
            ]

        @pytest.mark.asyncio
        async def test_load_devices_without_connection_raises(self):
            """load_devices() без соединения вызывает DatabaseError."""
            db = PostgresStorage(connstr="postgresql://testdb")
            with pytest.raises(
                psycopg.DatabaseError,
                match="Connection not established"
            ):
                await db.load_devices()

        @pytest.mark.asyncio
        async def test_load_devices_no_params_in_sql(
            self,
            storage: PostgresStorage,
            mock_cursor: AsyncMock
        ):
            """load_devices выполняет SELECT без дополнительных параметров."""
            mock_cursor.fetchall.return_value = []
            await storage.load_devices()

            last_call = mock_cursor.execute.call_args_list[-1]
            # execute вызывается только с sql, без параметров
            assert len(last_call[0]) == 1
