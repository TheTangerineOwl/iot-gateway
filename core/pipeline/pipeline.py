from models.message import Message
from .stages import PipelineStage


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
        print(f"Pipeline stage added: {stage.name}")

    def remove_stage(self, stage_name: str) -> None:
        self.stages = [s for s in self.stages if s.name != stage_name]

    async def setup(self):
        for stage in self.stages:
            await stage.setup()
        print(
            f"Pipeline initialized with {len(self.stages)} "
            f"stages: {[s.name for s in self.stages]}"
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
                    print(
                        f"Message {message.message_id} "
                        f"filtered at stage '{stage.name}'"
                    )
                    return None
                current = result
            except Exception:
                self.error_count += 1
                print(
                    f"Pipeline error at stage '{stage.name}' "
                    f"for message {stage.name}: {message.message_id}"
                )

        current.processed = True
        self.processed_count += 1
        return current
