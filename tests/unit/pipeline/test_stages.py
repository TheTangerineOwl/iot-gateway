"""Тесты этапов конвейера."""
from math import nan, inf
import pytest
from core.pipeline import Pipeline
from core.pipeline.stages import (
    ValidationStage, AuthorizationStage, CleanupStage
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

    msg = Message(device_id="UNAUTH", payload={"value": 1})
    result = await pipeline.execute(msg)

    assert result is None
    assert pipeline.stats["filtered"] == 1


@pytest.mark.asyncio
async def test_auth_error_status(registry, device, telemetry_message):
    """Сообщения от девайса с ошибкой фильтруются."""
    pipeline = Pipeline()
    pipeline.add_stage(AuthorizationStage(registry))
    await pipeline.setup()

    device.device_id = 'ERR_STATUS'
    device.device_status = DeviceStatus.ERROR
    await registry.register(device)

    result = await pipeline.execute(telemetry_message)

    assert result is None
    assert pipeline.stats["filtered"] == 1


# Тест санитизации.
@pytest.mark.asyncio
async def test_cleanup_correct_passes(telemetry_message):
    """Сообщения с корректными значениями проходят."""
    pipeline = Pipeline()
    pipeline.add_stage(CleanupStage())
    await pipeline.setup()

    result = await pipeline.execute(telemetry_message)

    assert result is not None
    assert result.processed is True
    assert pipeline.stats["processed"] == 1


@pytest.mark.asyncio
async def test_cleanup_float_full():
    """Если все поля в нагрузке некорректны, сообщение фильтруется."""
    pipeline = Pipeline()
    pipeline.add_stage(CleanupStage())
    await pipeline.setup()

    msg = Message(
        device_id="dev-1",
        payload={
            'floatNaN': nan,
            'floatInf': inf
        }
    )
    result = await pipeline.execute(msg)

    assert result is None
    assert pipeline.stats["filtered"] == 1


@pytest.mark.asyncio
async def test_cleanup_float_partial():
    """Если часть нагрузки некорректна, остальное сохраняется."""
    pipeline = Pipeline()
    pipeline.add_stage(CleanupStage())
    await pipeline.setup()

    msg = Message(
        device_id="dev-1",
        payload={
            'float_bad': nan,
            'float_good': 19.0
        }
    )
    result = await pipeline.execute(msg)

    assert result is not None
    assert result.processed is True
    assert pipeline.stats["processed"] == 1

    assert result.payload.get('float_bad', None) is None
    assert result.payload.get('float_good', None) is not None
    assert result.payload.get('float_good', None) == 19.0
