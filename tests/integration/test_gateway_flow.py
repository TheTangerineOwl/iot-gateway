"""Общий поток теста шлюза."""
import pytest
import pytest_asyncio
import asyncio
from core.message_bus import MessageBus
from core.pipeline.pipeline import Pipeline
from core.pipeline.stages import ValidationStage
from storage.subscriber import StorageSubscriber
from models.message import Message


@pytest_asyncio.fixture
async def full_flow(mock_storage):
    """Полный поток работы шлюза."""
    bus = MessageBus(max_queue=100)
    await bus.start()

    pipeline = Pipeline()
    pipeline.add_stage(ValidationStage())
    await pipeline.setup()

    subscriber = StorageSubscriber(mock_storage)

    async def handle_telemetry(message: Message):
        result = await pipeline.execute(message)
        if result:
            result.processed = True
            await bus.publish(
                f"processed.telemetry.{result.device_id}",
                result
            )

    bus.subscribe("telemetry.*", handle_telemetry)
    bus.subscribe("processed.telemetry.*", subscriber.handle)

    yield bus, mock_storage

    await bus.stop()
    await pipeline.teardown()


@pytest.mark.asyncio
async def test_valid_message_reaches_storage(full_flow, telemetry_message):
    """Корректное сообщение проходит весь путь и сохраняется."""
    bus, storage = full_flow

    await bus.publish("telemetry.dev-1", telemetry_message)
    await asyncio.sleep(0.1)

    storage.save.assert_awaited_once()
    record = storage.save.call_args[0][0]
    assert record.device_id == "dev-1"


@pytest.mark.asyncio
async def test_invalid_message_not_saved(full_flow):
    """Сообщение без device_id отфильтровывается pipeline и не сохраняется."""
    bus, storage = full_flow

    bad_msg = Message(device_id="", payload={"x": 1})
    await bus.publish("telemetry.dev-1", bad_msg)
    await asyncio.sleep(0.1)

    storage.save.assert_not_awaited()
