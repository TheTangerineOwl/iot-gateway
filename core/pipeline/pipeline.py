"""Конвейер для обработки сообщений на шине."""
import logging
from models.message import Message
from .stages import PipelineStage


logger = logging.getLogger(__name__)


class Pipeline:
    """Класс конвейера по обработке сообщений."""

    def __init__(self) -> None:
        """Конвейер по обработке сообщений."""
        self._stages: list[PipelineStage] = []
        self._processed_count = 0
        self._filtered_count = 0
        self._error_count = 0

    @property
    def stats(self) -> dict[str, int]:
        """Статистика работы конвейера."""
        return {
            "stages": len(self._stages),
            "processed": self._processed_count,
            "filtered": self._filtered_count,
            "errors": self._error_count,
        }

    @property
    def stages(self) -> list[str]:
        """Имена этапов конвейера."""
        return [s.name for s in self._stages]

    def add_stage(self, stage: PipelineStage) -> None:
        """Добавить этап в конвейер."""
        self._stages.append(stage)
        logger.info("Pipeline stage added: %s", stage.name)

    def remove_stage(self, stage_name: str) -> None:
        """Удалить этап из конвейера."""
        self._stages = [s for s in self._stages if s.name != stage_name]

    async def setup(self) -> None:
        """Инициализировать конвейер."""
        for stage in self._stages:
            await stage.setup()
        logger.info(
            "Pipeline initialized with %d stages: %s",
            len(self._stages),
            [s.name for s in self._stages]
        )

    async def teardown(self) -> None:
        """Деинициализировать конвейер."""
        for stage in self._stages:
            await stage.teardown()

    async def execute(self, message: Message) -> Message | None:
        """Обработать сообщение."""
        current = message

        for stage in self._stages:
            try:
                result = await stage.process(current)
                if result is None:
                    self._filtered_count += 1
                    logger.info(
                        "Message %s filtered at stage '%s'",
                        message.message_id,
                        stage.name
                    )
                    return None
                current = result
            except Exception as ex:
                self._error_count += 1
                logger.error(
                    "Pipeline error at stage '%s' "
                    "for message %s: %s",
                    stage.name, message.message_id, ex, exc_info=True
                )

        current.processed = True
        self._processed_count += 1
        return current
