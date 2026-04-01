from abc import ABC, abstractmethod
from typing import Any
from models.message import Message


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
            print("Message discarded: no device_id")
            return None
        if not message.payload:
            print(
                "Message discarded: empty payload from %s", message.device_id
            )
            return None
        return message
