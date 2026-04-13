"""Тест записи телеметрии."""
from models.message import Message
from models.telemetry import TelemetryRecord


class TestTelemetryRecord:
    """Тест записи телеметрии."""

    def test_from_message(
        self, telemetry_message: Message
    ):
        """Тест преобразования сообщения в запись."""
        record = TelemetryRecord.from_message(telemetry_message)
        assert record.message_id == telemetry_message.message_id
        assert record.device_id == telemetry_message.device_id
        assert record.payload == telemetry_message.payload
        assert record.timestamp == telemetry_message.timestamp
        assert record.protocol == telemetry_message.protocol
