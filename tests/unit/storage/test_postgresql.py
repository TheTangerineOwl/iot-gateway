"""Тест хранилища PostgreSQL."""
import pytest
import pytest_asyncio
from datetime import datetime, timezone
import json
import psycopg
from unittest.mock import AsyncMock, MagicMock, patch
from storage.base import CREATE_TABLE, INSERT_SQL
from storage.postgresql import PostgresStorage
from models.telemetry import TelemetryRecord


def make_record(**kwargs) -> TelemetryRecord:
    """Создать запись телеметрии."""
    defaults = dict(
        device_id='dev-001',
        payload={'temp': 36.6},
        message_id='msg-001',
        protocol='http'
    )
    return TelemetryRecord(**(defaults | kwargs))


@pytest.fixture
def mock_cursor():
    """Мок курсора."""
    cur = AsyncMock()
    cur.__aenter__ = AsyncMock(return_value=cur)
    cur.__aexit__ = AsyncMock(return_value=False)
    cur.fetchall = AsyncMock(return_value=[])
    return cur


@pytest.fixture
def mock_conn(mock_cursor):
    """Мок подключения."""
    conn = AsyncMock()
    conn.cursor = MagicMock(return_value=mock_cursor)
    conn.commit = AsyncMock()
    conn.close = AsyncMock()
    return conn


@pytest_asyncio.fixture
async def storage(mock_conn):
    """Тестовое хранилище."""
    with patch(
        'storage.postgresql.AsyncConnection.connect',
        return_value=mock_conn
    ):
        db = PostgresStorage(connstr='postgresql://testdb')
        await db.setup()
        yield db


@pytest.mark.asyncio
async def test_setup_create_tb(storage, mock_conn, mock_cursor):
    """При запуске хранилища создается подключение и таблица."""
    assert storage._conn is not None
    mock_cursor.execute.assert_awaited_once()
    assert mock_cursor.execute.call_args[0][0] == CREATE_TABLE
    mock_conn.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_teardown_close_conn(storage, mock_conn):
    """При остановке хранилища подключение закрывается."""
    await storage.teardown()
    mock_conn.close.assert_awaited_once()
    assert storage._conn is None


@pytest.mark.asyncio
async def test_teardown_wo_setup_raise():
    """При остановке хранилища без запуска возникает ошибка."""
    db = PostgresStorage(connstr='postgresql://testdb')
    with pytest.raises(
        psycopg.DatabaseError,
        match='Connection not established'
    ):
        await db.teardown()


@pytest.mark.asyncio
async def test_save_execute_insert(storage, mock_cursor):
    """При вызове save запись сохраняется с помощью INSERT."""
    record = make_record()
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
async def test_save_commits(storage, mock_conn):
    """save() должен вызвать commit после INSERT."""
    await storage.save(make_record())

    # commit вызывался минимум дважды: в setup() и в save()
    assert mock_conn.commit.await_count >= 2


@pytest.mark.asyncio
async def test_save_without_connection_raises():
    """save() без соединения → DatabaseError."""
    db = PostgresStorage(connstr="postgresql://testdb")
    with pytest.raises(
        psycopg.DatabaseError,
        match="Connection not established"
    ):
        await db.save(make_record())


@pytest.mark.asyncio
async def test_save_payload_serialized_as_json(storage, mock_cursor):
    """Поле payload сериализуется в JSON-строку, не в dict."""
    record = make_record(payload={"nested": {"x": 1}, "list": [1, 2, 3]})
    await storage.save(record)

    last_call = mock_cursor.execute.call_args_list[-1]
    _, params = last_call[0]
    payload_arg = params[3]

    assert isinstance(payload_arg, str)
    assert json.loads(payload_arg) == record.payload


@pytest.mark.asyncio
async def test_get_by_device_empty(storage, mock_cursor):
    """get_by_device() возвращает пустой список, если нет записей."""
    mock_cursor.fetchall.return_value = []

    result = await storage.get_by_device("dev-001")

    assert result == []


@pytest.mark.asyncio
async def test_get_by_device_returns_records(storage, mock_cursor):
    """get_by_device() возвращает список записей с правильными полями."""
    ts = datetime.now(timezone.utc)
    mock_cursor.fetchall.return_value = [
        {
            "message_id": "msg-001",
            "device_id":  "dev-001",
            "protocol":   "http",
            "payload":    json.dumps({"temp": 36.6}),
            "timestamp":  ts,
        }
    ]

    result = await storage.get_by_device("dev-001")

    assert len(result) == 1
    r = result[0]
    assert r.device_id == "dev-001"
    assert r.message_id == "msg-001"
    assert r.protocol == "http"
    assert r.payload == {"temp": 36.6}
    assert r.timestamp == ts


@pytest.mark.asyncio
async def test_get_by_device_multiple_records(storage, mock_cursor):
    """get_by_device() возвращает все строки из fetchall."""
    mock_cursor.fetchall.return_value = [
        {"message_id": f"msg-00{i}", "device_id": "dev-001",
         "protocol": "http", "payload": "{}", "timestamp": None}
        for i in range(5)
    ]

    result = await storage.get_by_device("dev-001")
    assert len(result) == 5


@pytest.mark.asyncio
async def test_get_by_device_without_connection_raises():
    """get_by_device() без соединения вызывает DatabaseError."""
    db = PostgresStorage(connstr="postgresql://testdb")
    with pytest.raises(
        psycopg.DatabaseError,
        match="Connection not established"
    ):
        await db.get_by_device("dev-001")


@pytest.mark.asyncio
async def test_get_by_device_passes_limit(storage, mock_cursor):
    """get_by_device() передаёт limit вторым параметром в execute."""
    mock_cursor.fetchall.return_value = []

    await storage.get_by_device("dev-001", limit=42)

    last_call = mock_cursor.execute.call_args_list[-1]
    _, params = last_call[0]
    assert params == ("dev-001", 42)
