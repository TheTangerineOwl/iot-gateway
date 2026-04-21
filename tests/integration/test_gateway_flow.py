"""Общий поток теста шлюза."""
import pytest
import pytest_asyncio
import asyncio
from config.config import YAMLConfigLoader
from config.topics import TopicKey, TopicManager
from core.message_bus import MessageBus
from core.pipeline.pipeline import Pipeline
from core.pipeline.stages import ValidationStage
from storage.subscriber import StorageSubscriber
from models.message import Message


@pytest_asyncio.fixture
async def full_flow(topics: TopicManager, mock_storage):
    """Полный поток работы шлюза."""
    bus = MessageBus(YAMLConfigLoader())
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
                topics.get(
                    TopicKey.PROCESSED_TELEMETRY,
                    device_id=result.device_id
                ),
                result
            )

    bus.subscribe(
        topics.get_subscription_pattern(TopicKey.DEVICES_TELEMETRY),
        handle_telemetry
    )
    bus.subscribe(
        topics.get_subscription_pattern(
            TopicKey.PROCESSED_TELEMETRY
        ),
        subscriber.handle
    )

    yield bus, mock_storage

    await bus.stop()
    await pipeline.teardown()


@pytest.mark.asyncio
async def test_valid_message_reaches_storage(
    topics: TopicManager,
    full_flow,
    telemetry_message
):
    """Корректное сообщение проходит весь путь и сохраняется."""
    bus, storage = full_flow

    await bus.publish(
        topics.get(TopicKey.DEVICES_TELEMETRY, device_id="dev-001"),
        telemetry_message
    )
    await asyncio.sleep(0.1)

    storage.save.assert_awaited_once()
    record = storage.save.call_args[0][0]
    assert record.device_id == "dev-001"


@pytest.mark.asyncio
async def test_invalid_message_not_saved(topics: TopicManager, full_flow):
    """Сообщение без device_id отфильтровывается pipeline и не сохраняется."""
    bus, storage = full_flow

    bad_msg = Message(device_id="", payload={"x": 1})
    await bus.publish(
        topics.get(TopicKey.DEVICES_TELEMETRY, device_id="dev-001"),
        bad_msg
    )
    await asyncio.sleep(0.1)

    storage.save.assert_not_awaited()
