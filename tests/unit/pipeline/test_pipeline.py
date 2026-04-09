"""Тест модуля конвейера обработки  сообщдений."""
import pytest
from core.pipeline.pipeline import Pipeline
from core.pipeline.stages import PipelineStage


class PassThroughStage(PipelineStage):
    """Проходная стадия, ничего не делает с сообщением."""

    name = "passthrough"

    async def process(self, message):
        """Обработка сообщений."""
        return message


class FilterStage(PipelineStage):
    """Полный фильтр сообщений."""

    name = "filter"

    async def process(self):
        """Обработка сообщений."""
        return None


@pytest.mark.asyncio
async def test_stage_order(telemetry_message):
    """Этапы вызываются строго по порядку."""
    order = []

    class FirstStage(PipelineStage):
        """Первая стадия конвейера."""

        name = "first_stage"

        async def process(self, msg):
            """Обработка стадии."""
            order.append("first")
            return msg

    class SecondStage(PipelineStage):
        """Вторая стадия конвейера."""

        name = "second"

        async def process(self, msg):
            """Обработка стадии."""
            order.append("second")
            return msg

    pipeline = Pipeline()
    pipeline.add_stage(FirstStage())
    pipeline.add_stage(SecondStage())
    await pipeline.setup()
    await pipeline.execute(telemetry_message)

    assert order == ["first", "second"]


@pytest.mark.asyncio
async def test_stage_error_count(telemetry_message):
    """Ошибка обработки не ломает все и добавляет счетчик."""
    class BrokenStage(PipelineStage):
        """Сломанный этап конвейера."""

        name = "broken"

        async def process(self, msg):
            """Обработка стадии."""
            raise ValueError("Test stage fail")

    pipeline = Pipeline()
    pipeline.add_stage(BrokenStage())
    await pipeline.setup()
    await pipeline.execute(telemetry_message)

    assert pipeline.stats["errors"] == 1
