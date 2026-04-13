"""Общие фикстуры для тестов протоколов."""
import pytest
import json
from models.message import Message, MessageType
from tests.conftest import (
    DEVICE_DEF_ID,
    MSG_DEF_ID,
    MSG_DEF_TOPIC,
    MSG_DEF_PAYLOAD,
    MSG_DEF_PROTOCOL,
    MSG_DEF_TYPE,
    MSG_DEF_META,
    MSG_DEF_SCHEMA,
)


def json_payload(data: dict) -> bytes:
    """Сериализовать словарь в байты JSON."""
    return json.dumps(data).encode()


def parse_response(msg: bytes) -> dict:
    """Десериализовать payload ответа из JSON."""
    return json.loads(msg.decode())


@pytest.fixture
def telemetry_body() -> dict:
    """Минимальное корректное тело запроса телеметрии."""
    return {
        'device_id': DEVICE_DEF_ID,
        'payload': MSG_DEF_PAYLOAD,
    }


@pytest.fixture
def register_body() -> dict:
    """Минимальное корректное тело запроса регистрации."""
    return {
        'device_id': DEVICE_DEF_ID,
        'name': 'Sensor A',
    }


@pytest.fixture
def message() -> Message:
    """Тестовое сообщение телеметрии."""
    return Message(
        message_id=MSG_DEF_ID,
        device_id=DEVICE_DEF_ID,
        message_type=MSG_DEF_TYPE,
        message_topic=MSG_DEF_TOPIC,
        payload=MSG_DEF_PAYLOAD,
        protocol=MSG_DEF_PROTOCOL,
        schema_version=MSG_DEF_SCHEMA,
        metadata=MSG_DEF_META,
    )


@pytest.fixture
def registration_message() -> Message:
    """Тестовое сообщение регистрации."""
    return Message(
        message_id=MSG_DEF_ID,
        device_id=DEVICE_DEF_ID,
        message_type=MessageType.REGISTRATION,
        message_topic=f'device.register.{DEVICE_DEF_ID}',
        payload={'name': 'Sensor A'},
        protocol=MSG_DEF_PROTOCOL,
        schema_version=MSG_DEF_SCHEMA,
        metadata={},
    )
