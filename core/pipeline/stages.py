"""Этапы обработки сообщения на конвейере."""
import logging
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
                "Message discarded: empty payload from %d", message.device_id
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
