"""Тест модуля конвейера обработки  сообщдений."""
import pytest
from core.pipeline.pipeline import Pipeline
from core.pipeline.stages import ValidationStage, PipelineStage
from models.message import Message


class PassThroughStage(PipelineStage):
    """Проходная стадия, ничего не делает с сообщением."""

    name = "passthrough"

    async def process(self, message):
        """Обработка сообщений."""
        return message


class FilterStage(PipelineStage):
    """Полный фильтр сообщений."""

    name = "filter"

    async def process(self, message):
        """Обработка сообщений."""
        return None


@pytest.mark.asyncio
async def test_valid_passes(telemetry_message):
    """Корректное сообщение должно проходить свободно."""
    pipeline = Pipeline()
    pipeline.add_stage(ValidationStage())
    await pipeline.setup()

    result = await pipeline.execute(telemetry_message)

    assert result is not None
    assert result.processed is True
    assert pipeline.stats["processed"] == 1


@pytest.mark.asyncio
async def test_filter_wo_device_id():
    """Сообщения без device_id должны отсеиваться."""
    pipeline = Pipeline()
    pipeline.add_stage(ValidationStage())
    await pipeline.setup()

    msg = Message(device_id="", payload={"value": 1})
    result = await pipeline.execute(msg)

    assert result is None
    assert pipeline.stats["filtered"] == 1


@pytest.mark.asyncio
async def test_filter_empty():
    """Пустые (без нагрузки) сообщения должны отсеиваться."""
    pipeline = Pipeline()
    pipeline.add_stage(ValidationStage())
    await pipeline.setup()

    msg = Message(device_id="dev-1", payload={})
    result = await pipeline.execute(msg)

    assert result is None


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
            raise ValueError("fail")

    pipeline = Pipeline()
    pipeline.add_stage(BrokenStage())
    await pipeline.setup()
    await pipeline.execute(telemetry_message)

    assert pipeline.stats["errors"] == 1
