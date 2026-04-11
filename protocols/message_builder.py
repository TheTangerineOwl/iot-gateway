"""Класс для построения сообщений-словарей по шаблону."""
from enum import Enum
from typing import Any
from models.message import Message, MessageType
from models.device import ProtocolType


class CommonErrMsg(str, Enum):
    """Частые типы ошибок сообщений."""

    INVALID_JSON = 'Invalid JSON'
    MISSING_DEVICE_ID = 'device_id is required'
    INTERNAL_SERVER_ERROR = 'Server error'
    UNKNOWN = 'Unknown error'


class MessageBuilder:
    """Метод для построения JSON-сообщений."""

    @staticmethod
    def err_from_str(
        error_code: str,
        error_msg: str
    ):
        """Строит сообщение об ошибке из заданных полей."""
        return {
            'status': 'error',
            'error_code': error_code,
            'error_msg': error_msg
        }

    @staticmethod
    def err_from_status(
        error_status: CommonErrMsg
    ):
        """Строит сообщение об ошибке из типа ошибки."""
        return MessageBuilder.err_from_str(
            error_code=error_status.name,
            error_msg=error_status.value
        )

    @staticmethod
    def build_msg(
        message: Message | None = None,
        status: str = 'ok',
        **kwargs
    ):
        """Строит сообщение из заданных полей."""
        standard: dict[str, Any]
        if not message:
            standard = {'status': status}
        else:
            standard = {
                'status': status,
                'message_id': message.message_id,
                'schema_version': message.schema_version,
                'timestamp': message.timestamp
            }
        for k, v in kwargs.items():
            standard[k] = v
        return standard

    # в дальнейшем будет настройка через yaml, пока так
    _INCLUDE_IN_PAYLOAD: dict[str, set[str]] = {
        'all': set(),
        MessageType.REGISTRATION: {
            'device_id', 'name', 'device_type',
            'protocol', 'device_status', 'last_response', 'created_at',
        },
        MessageType.STATUS: set(
            'device_status',
        )
    }

    _EXCLUDE_IN_PAYLOAD: dict[str, set[str]] = {
        'all': {
            'schema_version', 'timestamp', 'payload',
            'device_id', 'name', 'device_type',
            'protocol', 'device_status', 'last_response', 'created_at',
        },
    }

    @staticmethod
    def normalize(
        body: dict[str, Any],
        protocol_name: ProtocolType = ProtocolType.UNKNOWN,
        topic: str = '',
        proto_meta: Any | None = None,
        message_type: MessageType = MessageType.TELEMETRY
    ) -> Message:
        """Приводит сообщения к единому формату."""
        device_id = str(body.get('device_id', ''))

        if 'payload' in body:
            payload = body['payload']
            del body['payload']
        else:
            payload = dict()

        fields = set(k for k in body.keys())
        to_include = set.union(
            MessageBuilder._INCLUDE_IN_PAYLOAD.get('all', set()),
            MessageBuilder._INCLUDE_IN_PAYLOAD.get(message_type, set())
        )
        to_exclude = set.union(
            MessageBuilder._EXCLUDE_IN_PAYLOAD.get('all', set()),
            MessageBuilder._EXCLUDE_IN_PAYLOAD.get(message_type, set())
        )
        to_exclude = to_exclude.difference(to_include)
        fields = fields.difference(to_exclude)

        for key in fields:
            payload[key] = body[key]

        schema_version = str(body.get('schema_version', '1.0'))

        return Message(
            message_topic=topic,
            message_type=message_type,
            device_id=device_id,
            protocol=protocol_name,
            schema_version=schema_version,
            payload=payload,
            metadata={
                protocol_name: proto_meta
            } if proto_meta
            else {}
        )

    @staticmethod
    def err_miss_dev_id():
        """Возвращает сообщение о пропущенном device_id."""
        return MessageBuilder.err_from_status(
            CommonErrMsg.MISSING_DEVICE_ID
        )

    @staticmethod
    def err_inval_json():
        """Возвращает сообщение о некорректном формате."""
        return MessageBuilder.err_from_status(
            CommonErrMsg.INVALID_JSON
        )

    @staticmethod
    def err_internal(reason: str):
        """Возвращает сообщение о внутренней ошибке."""
        return MessageBuilder.err_from_str(
            error_code=CommonErrMsg.INTERNAL_SERVER_ERROR,
            error_msg=reason
        )
