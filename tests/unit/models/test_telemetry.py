"""Тест записи телеметрии."""
import pytest
from models.message import Message
from models.telemetry import TelemetryRecord
from tests.conftest import not_raises


class TestTelemetryRecord:
    """Тест записи телеметрии."""

    def test_from_message(
        self, telemetry_message: Message
    ):
        """Тест преобразования сообщения в запись."""
        with not_raises(Exception):
            record = TelemetryRecord.from_message(telemetry_message)
        assert record.message_id == telemetry_message.message_id
        assert record.device_id == telemetry_message.device_id
        assert record.payload == telemetry_message.payload
        assert record.timestamp == telemetry_message.timestamp
        assert record.protocol == telemetry_message.protocol

    def test_to_dict(self, record: TelemetryRecord):
        """Возвращается правильный словарь."""
        with not_raises(Exception):
            record_dict = record.to_dict()
        assert record.device_id == record_dict.get('device_id')
        assert record.message_id == record_dict.get('message_id')
        assert record.payload == record_dict.get('payload')
        assert record.protocol.value == record_dict.get('protocol')
        assert record.timestamp == record_dict.get('timestamp')

    def test_from_dict(self, record: TelemetryRecord):
        """Правильно десериализируется из словаря."""
        record_dict = {
            'device_id': record.device_id,
            'payload': record.payload,
            'timestamp': record.timestamp,
            'message_id': record.message_id,
            'protocol': record.protocol.value
        }
        with not_raises(Exception):
            new_record = TelemetryRecord.from_dict(record_dict)
        assert new_record == record

    def test_dict_roundtrip(self, record: TelemetryRecord):
        """При использовании to_dict + from_dict получится то же сообщение."""
        with not_raises(Exception):
            new_record = TelemetryRecord.from_dict(record.to_dict())
        assert new_record == record

    def test_from_dict_default(self):
        """При передаче пустого словаря from_dict дает дефолты."""
        record_dict = dict()
        with pytest.raises(
            ValueError,
            match='device_id is required'
        ):
            record = TelemetryRecord.from_dict(record_dict)
        record_dict['device_id'] = ''
        with pytest.raises(
            ValueError,
            match='empty payload'
        ):
            record = TelemetryRecord.from_dict(record_dict)
        record_dict['payload'] = dict()
        with not_raises(Exception):
            record = TelemetryRecord.from_dict(record_dict)
        comp_record = TelemetryRecord('', dict())
        # всегда будет отличаться из-за time в конструкторе
        comp_record.timestamp = record.timestamp
        assert comp_record == record
