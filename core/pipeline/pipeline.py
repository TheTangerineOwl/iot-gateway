import logging
from models.message import Message
from .stages import PipelineStage


logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self) -> None:
        self.stages: list[PipelineStage] = []
        self.processed_count = 0
        self.filtered_count = 0
        self.error_count = 0

    @property
    def stats(self) -> dict[str, int]:
        return {
            "stages": len(self.stages),
            "processed": self.processed_count,
            "filtered": self.filtered_count,
            "errors": self.error_count,
        }

    def add_stage(self, stage: PipelineStage):
        self.stages.append(stage)
        logger.info("Pipeline stage added: %s", stage.name)

    def remove_stage(self, stage_name: str) -> None:
        self.stages = [s for s in self.stages if s.name != stage_name]

    async def setup(self):
        for stage in self.stages:
            await stage.setup()
        logger.info(
            "Pipeline initialized with %d stages: %s",
            len(self.stages),
            [s.name for s in self.stages]
        )

    async def teardown(self) -> None:
        for stage in self.stages:
            await stage.teardown()

    async def execute(self, message: Message):
        current = message

        for stage in self.stages:
            try:
                result = await stage.process(current)
                if result is None:
                    self.filtered_count += 1
                    logger.info(
                        "Message %s filtered at stage '%s'",
                        message.message_id,
                        stage.name
                    )
                    return None
                current = result
            except Exception as ex:
                self.error_count += 1
                logger.error(
                    "Pipeline error at stage '%s' "
                    "for message %s: %s",
                    stage.name, message.message_id, ex, exc_info=True
                )

        current.processed = True
        self.processed_count += 1
        return current
