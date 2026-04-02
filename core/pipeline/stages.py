from abc import ABC, abstractmethod
import logging
from models.message import Message


logger = logging.getLogger(__name__)


class PipelineStage(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def process(self, message: Message) -> Message | None:
        pass

    async def setup(self) -> None:
        """Инициализация этапа (вызывается при старте pipeline)."""
        pass

    async def teardown(self) -> None:
        pass


class ValidationStage(PipelineStage):

    @property
    def name(self) -> str:
        return "validation"

    async def process(self, message: Message) -> Message | None:
        if not message.device_id:
            logger.info("Message discarded: no device_id")
            return None
        if not message.payload:
            logger.info(
                "Message discarded: empty payload from %d", message.device_id
            )
            return None
        return message
