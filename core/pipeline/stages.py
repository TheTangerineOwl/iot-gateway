"""Этапы обработки сообщения на конвейере."""
import logging
from math import isnan, isinf
from core.registry import DeviceRegistry
from models.message import Message
from models.device import DeviceStatus
from .base import PipelineStage


logger = logging.getLogger(__name__)


class ValidationStage(PipelineStage):
    """Этап простой валидации сообщения."""

    @property
    def name(self) -> str:
        """Имя этапа."""
        return "validation"

    async def process(self, message: Message) -> Message | None:
        """Валидация сообщения."""
        if not message.device_id:
            logger.info("Message discarded: no device_id")
            return None
        if not message.payload:
            logger.info(
                "Message discarded: empty payload from %s", message.device_id
            )
            return None
        return message


class AuthorizationStage(PipelineStage):
    """Этап проверки авторизации девайса."""

    @property
    def name(self) -> str:
        """Имя этапа."""
        return "authorization"

    def __init__(self, registry: DeviceRegistry) -> None:
        """Этап проверки регистрации девайса."""
        self._registry = registry

    async def process(self, message: Message) -> Message | None:
        """Проверка авторизации девайса, приславшего сообщение."""
        device = self._registry.get(message.device_id)
        if device is None:
            logger.warning(
                "Unauthorized device: %s", message.device_id
            )
            return None
        if device.device_status == DeviceStatus.ERROR:
            logger.warning(
                "Message from ERROR device ignored: %s", message.device_id
            )
            return None
        return message


class CleanupStage(PipelineStage):
    """Этап очистки некорректных значений."""

    @property
    def name(self):
        """Имя этапа."""
        return 'cleanup'

    async def process(self, message: Message) -> Message | None:
        """Удаление некорректных значений."""
        clean = {}
        for key, value in message.payload.items():
            if isinstance(value, float) and (isnan(value) or isinf(value)):
                logger.debug(
                    "Dropping invalid float '%s'=%s from %s",
                    key, value, message.device_id
                )
                continue
            clean[key] = value

        if not clean:
            logger.info(
                "Message %s dropped: payload empty after sanitization",
                message.message_id
            )
            return None

        message.payload = clean
        return message
