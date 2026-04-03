"""Тест хранилища SQLite."""
import pytest
import pytest_asyncio
from storage.sqlite import SQLiteStorage
from models.telemetry import TelemetryRecord


@pytest_asyncio.fixture
async def storage(tmp_path):
    """Тестовое подключение к БД."""
    db = SQLiteStorage(db_path=str(tmp_path / "test.db"))
    await db.setup()
    yield db
    await db.teardown()


@pytest.mark.asyncio
async def test_save_get(storage):
    """Сообщение должно сохраняться в БД."""
    record = TelemetryRecord(
        device_id="dev-1",
        payload={"temp": 36.6},
        message_id="msg-001",
        protocol="http",
    )
    await storage.save(record)

    results = await storage.get_by_device("dev-1")

    assert len(results) == 1
    assert results[0].device_id == "dev-1"
    assert results[0].payload == {"temp": 36.6}
    assert results[0].message_id == "msg-001"


@pytest.mark.asyncio
async def test_empty_if_unknown(storage):
    """Если девайс неизвестен, то возврат пустой."""
    results = await storage.get_by_device("unknown-device")
    assert results == []


@pytest.mark.asyncio
async def test_wo_connection():
    """Если подключение не установлено, то исключение."""
    storage = SQLiteStorage(db_path=":memory:")
    record = TelemetryRecord(device_id="x", payload={})

    # _conn = None
    with pytest.raises(Exception):
        await storage.save(record)
