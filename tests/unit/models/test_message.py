"""Тесты для модели сообщения."""
from time import time
from models.device import ProtocolType
from models.message import MessageType, Message
from tests.conftest import not_raises


class TestMessageType:
    """Тесты перечисления MessageType."""

    def test_register(self):
        """Определение типа не зависит от регистра."""
        entype = MessageType.TELEMETRY
        with not_raises(Exception):
            assert MessageType(entype.lower()) == MessageType.TELEMETRY
            assert MessageType(entype.upper()) == MessageType.TELEMETRY
            assert MessageType(entype.capitalize()) == MessageType.TELEMETRY

    def test_missing(self):
        """Если не может определелить тип, задает неизвестный."""
        typestr = 'some_type'
        with not_raises(Exception):
            result = MessageType(typestr)
        assert result == MessageType.UNKNOWN


class TestMessage:
    """Тесты сообщений."""

    def test_to_dict(self):
        """Возвращается правильный словарь."""
        time_created = time()
        message = Message(
            message_id='mes-test',
            message_type=MessageType.TELEMETRY,
            message_topic='test.topic',
            device_id='dev-id-test',
            protocol=ProtocolType.HTTP,
            schema_version='0.5',
            metadata={'meta': 'test'},
            payload={'value': 15.0},
            timestamp=time_created
        )
        message.processed = False
        msg_dict = message.to_dict()
        assert str(
            msg_dict.get('message_id')
        ) == 'mes-test'
        assert MessageType(
            msg_dict.get('message_type')
        ) == MessageType.TELEMETRY
        assert str(
            msg_dict.get('message_topic')
        ) == 'test.topic'
        assert str(
            msg_dict.get('device_id')
        ) == 'dev-id-test'
        assert ProtocolType(
            msg_dict.get('protocol')
        ) == ProtocolType.HTTP
        assert str(
            msg_dict.get('schema_version')
        ) == '0.5'
        assert msg_dict.get('metadata') == {'meta': 'test'}
        assert msg_dict.get('payload') == {'value': 15.0}
        assert msg_dict.get('timestamp') == time_created
        assert not bool(msg_dict.get('processed'))

    def test_from_dict(self):
        """Правильно десериализируется из словаря."""
        time_created = time()
        msg_dict = {
            'message_id': 'mes-id-test',
            'message_type': MessageType.TELEMETRY.value,
            'message_topic': 'test.topic',
            'device_id': 'dev-id-test',
            'payload': {'value': 15.0},
            'timestamp': time_created,
            'processed': True,
            'protocol': ProtocolType.HTTP.value,
            'schema_version': '0.5',
            'metadata': {'meta': 'test'}
        }
        with not_raises(Exception):
            message = Message.from_dict(msg_dict)
        assert message.device_id == 'dev-id-test'
        assert message.message_id == 'mes-id-test'
        assert message.message_type == MessageType.TELEMETRY
        assert message.message_topic == 'test.topic'
        assert message.payload == {'value': 15.0}
        assert message.timestamp == time_created
        assert message.processed
        assert message.protocol == ProtocolType.HTTP
        assert message.schema_version == '0.5'
        assert message.metadata == {'meta': 'test'}

    def test_dict_roundtrip(self):
        """При использовании to_dict + from_dict получится то же сообщение."""
        time_created = time()
        message = Message(
            message_id='mes-test',
            message_type=MessageType.TELEMETRY,
            message_topic='test.topic',
            device_id='dev-id-test',
            protocol=ProtocolType.HTTP,
            schema_version='0.5',
            metadata={'meta': 'test'},
            payload={'value': 15.0},
            timestamp=time_created
        )
        new_message = Message.from_dict(message.to_dict())
        assert new_message == message

    def test_from_dict_default(self):
        """При передаче пустого словаря from_dict дает дефолты."""
        default_msg = Message()
        with not_raises(Exception):
            message = Message.from_dict({})
        # так как задается новый uuid4, они не совпадут
        message.message_id = default_msg.message_id
        # не совпадут из-за задержки
        message.timestamp = default_msg.timestamp
        assert message == default_msg
