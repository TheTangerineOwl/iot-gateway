"""Тест модуля шины сообщений."""
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock
from core.message_bus import MessageBus


@pytest_asyncio.fixture
async def running_bus():
    """Рабочая шина."""
    bus = MessageBus(max_queue=100)
    await bus.start()
    yield bus
    await bus.stop()


@pytest.mark.asyncio
async def test_deliver(running_bus, telemetry_message):
    """Сообщение доходит до подписчика."""
    handler = AsyncMock()
    running_bus.subscribe("telemetry.*", handler)

    await running_bus.publish("telemetry.dev-1", telemetry_message)
    await asyncio.sleep(0.05)

    handler.assert_awaited_once_with(telemetry_message)


@pytest.mark.asyncio
async def test_wrong_wild_prefix(
    running_bus,
    telemetry_message
):
    """processed.telemetry.* не совпадает с telemetry.*."""
    handler = AsyncMock()
    running_bus.subscribe("processed.telemetry.*", handler)

    await running_bus.publish("telemetry.dev-1", telemetry_message)
    await asyncio.sleep(0.05)

    handler.assert_not_awaited()


@pytest.mark.asyncio
async def test_priority_order(running_bus, telemetry_message):
    """Подписчик с высоким приоритетом вызывается первым."""
    call_order = []

    async def low(msg):
        """Обработчик подписчика с низким приоритетом."""
        call_order.append("low")

    async def high(msg):
        """Обработчик подписчика с высоким приоритетом."""
        call_order.append("high")

    running_bus.subscribe("telemetry.*", low,  priority=0)
    running_bus.subscribe("telemetry.*", high, priority=10)

    await running_bus.publish("telemetry.dev-1", telemetry_message)
    await asyncio.sleep(0.05)

    assert call_order == ["high", "low"]


@pytest.mark.asyncio
async def test_stats(running_bus, telemetry_message):
    """При удачной отправке статистика должна быть соответствующей."""
    running_bus.subscribe("telemetry.*", AsyncMock())
    await running_bus.publish("telemetry.dev-1", telemetry_message)
    await asyncio.sleep(0.05)

    assert running_bus.stats["published"] == 1
    assert running_bus.stats["delivered"] == 1
    assert running_bus.stats["errors"] == 0


@pytest.mark.asyncio
async def test_error_count(
    running_bus,
    telemetry_message
):
    """Ошибка в обработчике не кладёт шину, счётчик errors растёт."""
    async def bad_handler(msg):
        raise RuntimeError("kablow")

    running_bus.subscribe("telemetry.*", bad_handler)
    await running_bus.publish("telemetry.dev-1", telemetry_message)
    await asyncio.sleep(0.05)

    assert running_bus.stats["errors"] == 1
