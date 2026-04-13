"""Фикстуры для тестирования моделей."""
import pytest
from models.telemetry import TelemetryRecord
from tests.conftest import (
    DEVICE_DEF_ID, MSG_DEF_PAYLOAD, MSG_DEF_ID, MSG_DEF_PROTOCOL
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
