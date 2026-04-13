"""Тесты для MessageBuilder."""
from protocols.message_builder import (
    MessageBuilder,
    CommonErrMsg
)
from models.message import Message, MessageType
from models.device import ProtocolType


class TestCommonErrMsg:
    """Тесты для CommonErrMsg enum."""

    def test_enum_values(self):
        """Проверяет значения enum CommonErrMsg."""
        assert CommonErrMsg.INVALID_JSON == 'Invalid JSON'
        assert CommonErrMsg.MISSING_DEVICE_ID == 'device_id is required'
        assert CommonErrMsg.INTERNAL_SERVER_ERROR == 'Server error'
        assert CommonErrMsg.UNKNOWN == 'Unknown error'


class TestErrFromStr:
    """Тесты для метода err_from_str()."""

    def test_err_from_str_basic(self):
        """Создает базовое сообщение об ошибке из строк."""
        result = MessageBuilder.err_from_str(
            error_code='TEST_ERROR',
            error_msg='Test error message'
        )

        assert result == {
            'status': 'error',
            'error_code': 'TEST_ERROR',
            'error_msg': 'Test error message'
        }

    def test_err_from_str_empty_strings(self):
        """Обрабатывает пустые строки."""
        result = MessageBuilder.err_from_str(
            error_code='',
            error_msg=''
        )

        assert result == {
            'status': 'error',
            'error_code': '',
            'error_msg': ''
        }

    def test_err_from_str_special_characters(self):
        """Обрабатывает специальные символы в строках."""
        result = MessageBuilder.err_from_str(
            error_code='ERR_404',
            error_msg='Error: "Not found" & '
        )

        assert result['error_code'] == 'ERR_404'
        assert result['error_msg'] == 'Error: "Not found" & '


class TestErrFromStatus:
    """Тесты для метода err_from_status()."""

    def test_err_from_status_invalid_json(self):
        """Создает сообщение об ошибке."""
        result = MessageBuilder.err_from_status(
            CommonErrMsg.INVALID_JSON
        )

        assert result == {
            'status': 'error',
            'error_code': CommonErrMsg.INVALID_JSON.name,
            'error_msg': CommonErrMsg.INVALID_JSON.value
        }


class TestBuildMsg:
    """Тесты для метода build_msg()."""

    def test_build_msg_without_message(self):
        """Создает сообщение без объекта Message."""
        result = MessageBuilder.build_msg()

        assert result == {'status': 'ok'}

    def test_build_msg_without_message_custom_status(self):
        """Создает сообщение без Message с пользовательским статусом."""
        result = MessageBuilder.build_msg(status='pending')

        assert result == {'status': 'pending'}

    def test_build_msg_with_message(self, telemetry_message: Message):
        """Создает сообщение с объектом Message."""
        result = MessageBuilder.build_msg(message=telemetry_message)

        assert result['status'] == 'ok'
        assert result['message_id'] == telemetry_message.message_id
        assert result['schema_version'] == telemetry_message.schema_version
        assert result['timestamp'] == telemetry_message.timestamp

    def test_build_msg_with_message_custom_status(
        self,
        telemetry_message: Message
    ):
        """Создает сообщение с Message и пользовательским статусом."""
        result = MessageBuilder.build_msg(
            message=telemetry_message,
            status='completed'
        )

        assert result['status'] == 'completed'
        assert result['message_id'] == telemetry_message.message_id

    def test_build_msg_with_kwargs(self, telemetry_message: Message):
        """Добавляет дополнительные поля через kwargs."""
        result = MessageBuilder.build_msg(
            message=telemetry_message,
            device_id='dev-001',
            extra_field='extra_value'
        )

        assert result['device_id'] == 'dev-001'
        assert result['extra_field'] == 'extra_value'
        assert result['message_id'] == telemetry_message.message_id

    def test_build_msg_kwargs_without_message(self):
        """Добавляет kwargs без объекта Message."""
        result = MessageBuilder.build_msg(
            status='error',
            error_code='TEST',
            error_msg='Test error'
        )

        assert result == {
            'status': 'error',
            'error_code': 'TEST',
            'error_msg': 'Test error'
        }

    def test_build_msg_empty_kwargs(self, telemetry_message: Message):
        """Работает корректно с пустыми kwargs."""
        result = MessageBuilder.build_msg(message=telemetry_message)

        assert 'status' in result
        assert 'message_id' in result
        assert len(result) == 4


class TestNormalize:
    """Тесты для метода normalize()."""

    def test_normalize_basic_body(self):
        """Нормализует простое тело сообщения."""
        body = {
            'device_id': 'dev-001',
            'temperature': 25.5
        }

        result = MessageBuilder.normalize(body)

        assert isinstance(result, Message)
        assert result.device_id == 'dev-001'
        assert result.payload == {'temperature': 25.5}
        assert result.protocol == ProtocolType.UNKNOWN
        assert result.message_type == MessageType.TELEMETRY

    def test_normalize_with_payload(self):
        """Нормализует сообщение с явным payload."""
        body = {
            'device_id': 'dev-001',
            'payload': {'temperature': 25.5, 'humidity': 60}
        }

        result = MessageBuilder.normalize(body)

        assert result.device_id == 'dev-001'
        assert result.payload == {'temperature': 25.5, 'humidity': 60}

    def test_normalize_payload_deleted_from_body(self):
        """Удаляет payload из body после обработки."""
        body = {
            'device_id': 'dev-001',
            'payload': {'temp': 25}
        }

        MessageBuilder.normalize(body)

        assert 'payload' not in body

    def test_normalize_with_protocol(self):
        """Нормализует с указанным протоколом."""
        body = {'device_id': 'dev-001'}

        result = MessageBuilder.normalize(
            body,
            protocol=ProtocolType.HTTP
        )

        assert result.protocol == ProtocolType.HTTP

    def test_normalize_with_topic(self):
        """Нормализует с указанным топиком."""
        body = {'device_id': 'dev-001'}

        result = MessageBuilder.normalize(
            body,
            topic='test/topic'
        )

        assert result.message_topic == 'test/topic'

    def test_normalize_with_proto_meta(self):
        """Нормализует с метаданными протокола."""
        body = {'device_id': 'dev-001'}
        meta = {'client_id': 'client-123'}

        result = MessageBuilder.normalize(
            body,
            protocol=ProtocolType.MQTT,
            proto_meta=meta
        )

        assert result.metadata == {ProtocolType.MQTT: meta}

    def test_normalize_without_proto_meta(self):
        """Нормализует без метаданных протокола."""
        body = {'device_id': 'dev-001'}

        result = MessageBuilder.normalize(body)

        assert result.metadata == {}

    def test_normalize_with_message_type(self):
        """Нормализует с указанным типом сообщения."""
        body = {'device_id': 'dev-001'}

        result = MessageBuilder.normalize(
            body,
            message_type=MessageType.REGISTRATION
        )

        assert result.message_type == MessageType.REGISTRATION

    def test_normalize_registration_includes_device_fields(self):
        """При регистрации включает поля устройства в payload."""
        body = {
            'device_id': 'dev-001',
            'name': 'Thermometer',
            'device_type': 'sensor',
            'protocol': 'HTTP',
            'device_status': 'online',
            'last_response': 1234567890.0,
            'created_at': 1234567890.0,
            'extra_field': 'should_not_be_in_payload'
        }

        result = MessageBuilder.normalize(
            body,
            message_type=MessageType.REGISTRATION
        )

        assert 'name' in result.payload
        assert 'device_type' in result.payload
        assert 'protocol' in result.payload
        assert 'device_status' in result.payload
        assert 'last_response' in result.payload
        assert 'created_at' in result.payload
        assert 'device_id' in result.payload

    def test_normalize_status_includes_device_status(self):
        """При статусе включает device_status в payload."""
        body = {
            'device_id': 'dev-001',
            'device_status': 'online',
            'other_field': 'value'
        }

        result = MessageBuilder.normalize(
            body,
            message_type=MessageType.STATUS
        )

        assert 'device_status' in result.payload

    def test_normalize_telemetry_excludes_metadata_fields(self):
        """При телеметрии исключает метаданные из payload."""
        body = {
            'device_id': 'dev-001',
            'schema_version': '1.0',
            'timestamp': 1234567890.0,
            'temperature': 25.5
        }

        result = MessageBuilder.normalize(
            body,
            message_type=MessageType.TELEMETRY
        )

        assert 'schema_version' not in result.payload
        assert 'timestamp' not in result.payload
        assert 'device_id' not in result.payload
        assert 'temperature' in result.payload

    def test_normalize_with_schema_version(self):
        """Нормализует с версией схемы."""
        body = {
            'device_id': 'dev-001',
            'schema_version': '2.0'
        }

        result = MessageBuilder.normalize(body)

        assert result.schema_version == '2.0'

    def test_normalize_default_schema_version(self):
        """Использует версию схемы по умолчанию."""
        body = {'device_id': 'dev-001'}

        result = MessageBuilder.normalize(body)

        assert result.schema_version == '1.0'

    def test_normalize_empty_device_id(self):
        """Обрабатывает отсутствующий device_id."""
        body = {'temperature': 25.5}

        result = MessageBuilder.normalize(body)

        assert result.device_id == ''

    def test_normalize_device_id_conversion_to_string(self):
        """Преобразует device_id в строку."""
        body = {'device_id': 123}

        result = MessageBuilder.normalize(body)

        assert result.device_id == '123'
        assert isinstance(result.device_id, str)

    def test_normalize_preserves_original_payload(self):
        """Сохраняет оригинальный payload без изменений."""
        original_payload = {'temp': 25, 'humidity': 60}
        body = {
            'device_id': 'dev-001',
            'payload': original_payload.copy()
        }

        result = MessageBuilder.normalize(body)

        assert result.payload == original_payload

    def test_normalize_combines_payload_and_fields(self):
        """Комбинирует payload и дополнительные поля."""
        body = {
            'device_id': 'dev-001',
            'payload': {'temp': 25},
            'humidity': 60
        }

        result = MessageBuilder.normalize(body)

        assert result.payload == {'temp': 25, 'humidity': 60}

    def test_normalize_fields_priority_over_payload(self):
        """Поля из body имеют приоритет над payload."""
        body = {
            'device_id': 'dev-001',
            'payload': {'temp': 25},
            'temp': 30
        }

        result = MessageBuilder.normalize(body)

        assert result.payload['temp'] == 30
