"""Фикстуры для тестов хранилищ."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from models.telemetry import TelemetryRecord
from tests.conftest import (
    DEVICE_DEF_ID, MSG_DEF_ID, MSG_DEF_PAYLOAD, MSG_DEF_PROTOCOL
)


@pytest.fixture
def record() -> TelemetryRecord:
    """Тестовая запись хранилища."""
    return TelemetryRecord(
        device_id=DEVICE_DEF_ID,
        payload=MSG_DEF_PAYLOAD,
        message_id=MSG_DEF_ID,
        protocol=MSG_DEF_PROTOCOL
    )


@pytest_asyncio.fixture
async def mock_cursor():
    """Мок курсора."""
    cur = AsyncMock()
    cur.fetchall = AsyncMock(return_value=[])
    return cur


@pytest_asyncio.fixture
async def mock_conn(mock_cursor):
    """Мок подключения."""
    conn = AsyncMock()
    cursor_ctx = AsyncMock()
    cursor_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
    cursor_ctx.__aexit__ = AsyncMock(return_value=False)
    conn.cursor = MagicMock(return_value=cursor_ctx)
    conn.commit = AsyncMock()
    conn.close = AsyncMock()
    return conn
