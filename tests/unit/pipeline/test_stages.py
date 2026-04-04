"""Тесты этапов конвейера."""
import pytest
from core.pipeline import Pipeline
from core.pipeline.stages import (
    ValidationStage, AuthorizationStage
)
from models.device import DeviceStatus
from models.message import Message


# Тесты валидации.
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


# Тесты авторизации.
@pytest.mark.asyncio
async def test_authed_passes(telemetry_message, registry, device):
    """Сообщения от зарегистрированного девайса должны проходить."""
    pipeline = Pipeline()
    pipeline.add_stage(AuthorizationStage(registry))
    await pipeline.setup()

    await registry.register(device)

    result = await pipeline.execute(telemetry_message)

    assert result is not None
    assert result.processed is True
    assert pipeline.stats["processed"] == 1


@pytest.mark.asyncio
async def test_auth_wo_register(registry):
    """Сообщения от незарегистрированного device_id должны отсеиваться."""
    pipeline = Pipeline()
    pipeline.add_stage(AuthorizationStage(registry))
    await pipeline.setup()

    msg = Message(device_id="dev-001", payload={"value": 1})
    result = await pipeline.execute(msg)

    assert result is None
    assert pipeline.stats["filtered"] == 1


@pytest.mark.asyncio
async def test_auth_error_status(registry, device, telemetry_message):
    """."""
    pipeline = Pipeline()
    pipeline.add_stage(AuthorizationStage(registry))
    await pipeline.setup()

    device.device_status = DeviceStatus.ERROR
    await registry.register(device)

    result = await pipeline.execute(telemetry_message)

    assert result is None
    assert pipeline.stats["filtered"] == 1
