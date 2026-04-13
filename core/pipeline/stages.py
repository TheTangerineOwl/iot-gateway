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
        rejected = False
        rej_msg = 'Message rejected: '
        if not message.device_id:
            logger.info("Message discarded: no device_id")
            rej_msg += 'no device_id'
            rejected = True
        elif not message.payload:
            logger.info(
                "Message discarded: empty payload from %s", message.device_id
            )
            rej_msg += 'empty payload'
            rejected = True
        if rejected:
            message.metadata['reject_reason'] = rej_msg
            message.metadata['reject_stage'] = self.name
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
        rejected = False
        rej_msg = 'Message rejected: '

        device = self._registry.get(message.device_id)
        if device is None:
            logger.warning(
                "Unauthorized device: %s", message.device_id
            )
            rej_msg += 'unauthorized device'
            rejected = True
        elif device.device_status == DeviceStatus.ERROR:
            logger.warning(
                "Message from ERROR device ignored: %s", message.device_id
            )
            rej_msg += 'ERROR device status'
            rejected = True

        if rejected:
            message.metadata['reject_reason'] = rej_msg
            message.metadata['reject_stage'] = self.name
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
        rejected = False
        rej_msg = 'Message rejected: '

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
            rejected = True
            rej_msg += 'payload empty after sanitization'

        if rejected:
            message.metadata['reject_reason'] = rej_msg
            message.metadata['reject_stage'] = self.name
            return None

        message.payload = clean
        return message
