"""Тест хранилища SQLite."""
import pytest
import pytest_asyncio
import aiosqlite
from json import loads
from unittest.mock import AsyncMock
from storage.sqlite import (
    SQLiteStorage, SELECT_BY_DEVICE, CREATE_DEVICES_TABLE, UPSERT_DEVICE_SQL,
    DELETE_DEVICE_SQL, SELECT_ALL_DEVICES
)
from models.telemetry import TelemetryRecord
from models.device import Device, DeviceStatus, DeviceType, ProtocolType
from tests.conftest import not_raises


@pytest_asyncio.fixture
async def storage(tmp_path):
    """Тестовое подключение к БД."""
    db = SQLiteStorage(db_path=str(tmp_path / "test.db"))
    await db.setup()
    yield db
    await db.teardown()


class TestSQLConstants:
    """Проверяет наличие и корректность SQL-констант."""

    def test_create_devices_table_contains_device_id_pk(self):
        """CREATE_DEVICES_TABLE содержит device_id TEXT PRIMARY KEY."""
        assert "device_id" in CREATE_DEVICES_TABLE
        assert "PRIMARY KEY" in CREATE_DEVICES_TABLE

    def test_create_devices_table_contains_required_columns(self):
        """CREATE_DEVICES_TABLE содержит все необходимые колонки."""
        for col in ("name", "device_type", "device_status", "protocol",
                    "last_response", "created_at"):
            assert col in CREATE_DEVICES_TABLE

    def test_create_devices_table_is_create_if_not_exists(self):
        """CREATE_DEVICES_TABLE использует IF NOT EXISTS."""
        assert "IF NOT EXISTS" in CREATE_DEVICES_TABLE

    def test_upsert_device_sql_has_on_conflict(self):
        """UPSERT_DEVICE_SQL содержит ON CONFLICT для идемпотентного upsert."""
        assert "ON CONFLICT" in UPSERT_DEVICE_SQL

    def test_upsert_device_sql_updates_status(self):
        """UPSERT_DEVICE_SQL обновляет device_status при конфликте."""
        assert "device_status" in UPSERT_DEVICE_SQL

    def test_delete_device_sql_filters_by_device_id(self):
        """DELETE_DEVICE_SQL удаляет по device_id."""
        assert "device_id" in DELETE_DEVICE_SQL
        assert "DELETE" in DELETE_DEVICE_SQL.upper()

    def test_select_all_devices_selects_all_columns(self):
        """SELECT_ALL_DEVICES выбирает нужные поля."""
        for col in ("device_id", "name", "device_type", "device_status",
                    "protocol", "last_response", "created_at"):
            assert col in SELECT_ALL_DEVICES


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

    class TestUpsertDevice:
        """Тесты метода upsert_device."""

        @pytest.mark.asyncio
        async def test_insert_new_device(
            self,
            device: Device,
            storage
        ):
            """upsert_device вставляет новое устройство в БД."""
            await storage.upsert_device(device)

            devices = await storage.load_devices()
            ids = [d.device_id for d in devices]
            assert device.device_id in ids

        @pytest.mark.asyncio
        async def test_update_existing_device_status(
            self,
            device: Device,
            storage
        ):
            """upsert_device обновляет статус уже существующего устройства."""
            device.device_status = DeviceStatus.OFFLINE
            await storage.upsert_device(device)

            device.device_status = DeviceStatus.ONLINE
            await storage.upsert_device(device)

            devices = await storage.load_devices()
            saved = next(
                d for d in devices if d.device_id == device.device_id
            )
            assert saved.device_status == DeviceStatus.ONLINE

        @pytest.mark.asyncio
        async def test_upsert_preserves_created_at(
            self,
            device: Device,
            storage
        ):
            """upsert_device не меняет created_at при повторном вызове."""
            device.created_at = 1_700_000_000.0
            await storage.upsert_device(device)

            device.device_status = DeviceStatus.SLEEPING
            await storage.upsert_device(device)

            devices = await storage.load_devices()
            saved = next(
                d for d in devices if d.device_id == device.device_id
            )
            assert saved.created_at == pytest.approx(
                device.created_at,
                abs=1e-3
            )

        @pytest.mark.asyncio
        async def test_upsert_multiple_devices(self, storage):
            """upsert_device корректно работает для нескольких устройств."""
            devs = [Device(f"multi-{i}") for i in range(3)]
            for d in devs:
                await storage.upsert_device(d)

            loaded = await storage.load_devices()
            loaded_ids = {d.device_id for d in loaded}
            assert {"multi-0", "multi-1", "multi-2"}.issubset(loaded_ids)

        @pytest.mark.asyncio
        async def test_upsert_raises_without_connection(
            self,
            device,
            tmp_path
        ):
            """upsert_device бросает DatabaseError, если соединения нет."""
            db = SQLiteStorage(db_path=str(tmp_path / "testwconn.db"))
            with pytest.raises(aiosqlite.DatabaseError):
                await db.upsert_device(device)

        @pytest.mark.asyncio
        async def test_upsert_saves_all_fields(self, storage):
            """upsert_device сохраняет все поля устройства корректно."""
            ts_created = 1_600_000_000.0
            ts_last = 1_700_000_000.0
            device = Device(
                device_id="fields-check-001",
                name="Full Fields Device",
                device_type=DeviceType.ACTUATOR,
                device_status=DeviceStatus.SLEEPING,
                protocol=ProtocolType.MQTT,
                last_response=ts_last,
                created_at=ts_created,
            )
            await storage.upsert_device(device)

            devices = await storage.load_devices()
            saved = next(
                d for d in devices if d.device_id == "fields-check-001"
            )

            assert saved.name == "Full Fields Device"
            assert saved.device_type == DeviceType.ACTUATOR
            assert saved.device_status == DeviceStatus.SLEEPING
            assert saved.protocol == ProtocolType.MQTT
            assert saved.last_response == pytest.approx(ts_last, abs=1e-3)
            assert saved.created_at == pytest.approx(ts_created, abs=1e-3)

    class TestDeleteDevice:
        """Тесты метода delete_device."""

        @pytest.mark.asyncio
        async def test_delete_existing_device(
            self,
            device: Device,
            storage
        ):
            """delete_device удаляет ранее добавленное устройство."""
            await storage.upsert_device(device)
            await storage.delete_device(device.device_id)

            devices = await storage.load_devices()
            ids = [d.device_id for d in devices]
            assert device.device_id not in ids

        @pytest.mark.asyncio
        async def test_delete_nonexistent_device_no_error(self, storage):
            """delete_device не бросает ошибку при удалении несуществующего."""
            await storage.delete_device("ghost-device-999")

        @pytest.mark.asyncio
        async def test_delete_only_target_device(self, storage):
            """delete_device удаляет только целевое устройство."""
            for i in range(3):
                await storage.upsert_device(Device(f"del-multi-{i}"))

            await storage.delete_device("del-multi-1")

            devices = await storage.load_devices()
            ids = {d.device_id for d in devices}
            assert "del-multi-0" in ids
            assert "del-multi-1" not in ids
            assert "del-multi-2" in ids

        @pytest.mark.asyncio
        async def test_delete_raises_without_connection(self, tmp_path):
            """delete_device бросает DatabaseError, если соединения нет."""
            db = SQLiteStorage(db_path=str(tmp_path / "test.db"))
            with pytest.raises(aiosqlite.DatabaseError):
                await db.delete_device("some-id")

    class TestLoadDevices:
        """Тесты метода load_devices."""

        @pytest.mark.asyncio
        async def test_returns_empty_list_when_no_devices(self, storage):
            """load_devices возвращает пустой список, если устройств нет."""
            devices = await storage.load_devices()
            assert devices == []

        @pytest.mark.asyncio
        async def test_returns_all_inserted_devices(self, storage):
            """load_devices возвращает все вставленные устройства."""
            expected = [Device(f"load-{i}") for i in range(4)]
            for d in expected:
                await storage.upsert_device(d)

            loaded = await storage.load_devices()
            loaded_ids = {d.device_id for d in loaded}
            for d in expected:
                assert d.device_id in loaded_ids

        @pytest.mark.asyncio
        async def test_returns_device_instances(self, storage):
            """load_devices возвращает список объектов Device."""
            await storage.upsert_device(Device("instance-check-001"))

            devices = await storage.load_devices()
            assert all(isinstance(d, Device) for d in devices)

        @pytest.mark.asyncio
        async def test_count_matches_upserted(self, storage):
            """Количество возвращённых устройств совпадает со вставленными."""
            n = 5
            for i in range(n):
                await storage.upsert_device(Device(f"count-{i}"))

            devices = await storage.load_devices()
            assert len(devices) >= n

        @pytest.mark.asyncio
        async def test_raises_without_connection(self, tmp_path):
            """load_devices бросает DatabaseError, если соединения нет."""
            db = SQLiteStorage(db_path=str(tmp_path / "test.db"))
            with pytest.raises(aiosqlite.DatabaseError):
                await db.load_devices()

        @pytest.mark.asyncio
        async def test_enum_fields_deserialized_correctly(self, storage):
            """load_devices корректно десериализует enum-поля из строк БД."""
            device = Device(
                device_id="enum-deser-001",
                name="Enum Device",
                device_type=DeviceType.CONTROLLER,
                device_status=DeviceStatus.ERROR,
                protocol=ProtocolType.COAP,
            )
            await storage.upsert_device(device)

            devices = await storage.load_devices()
            saved = next(d for d in devices if d.device_id == "enum-deser-001")

            assert saved.device_type == DeviceType.CONTROLLER
            assert saved.device_status == DeviceStatus.ERROR
            assert saved.protocol == ProtocolType.COAP
