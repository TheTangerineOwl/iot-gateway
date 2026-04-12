"""Тесты этапов конвейера."""
from math import nan, inf
import pytest
from core.registry import DeviceRegistry
from core.pipeline import Pipeline
from core.pipeline.stages import (
    ValidationStage, AuthorizationStage, CleanupStage
)
from models.device import DeviceStatus, Device
from models.message import Message
from tests.conftest import not_raises


@pytest.fixture(scope='class')
def valid_stage():
    """Этап валидации."""
    return ValidationStage()


@pytest.fixture()
def auth_stage(registry: DeviceRegistry):
    """Этап проверки авторизации."""
    return AuthorizationStage(registry)


@pytest.fixture(scope='class')
def cleanup_stage():
    """Этап проверки корректных значений."""
    return CleanupStage()


class TestValidationStage:
    """Тесты для этапа валидации (ValidationStage)."""

    @pytest.mark.asyncio
    async def test_valid_passes(
        self,
        pipeline: Pipeline,
        valid_stage: ValidationStage,
        telemetry_message: Message
    ):
        """Корректное сообщение должно проходить свободно."""
        pipeline.add_stage(valid_stage)
        await pipeline.setup()

        with not_raises(Exception):
            result = await pipeline.execute(telemetry_message)

        assert result is not None
        assert result.processed is True
        assert pipeline.stats.get('processed', -1) == 1

    @pytest.mark.asyncio
    async def test_filter_wo_device_id(
        self,
        pipeline: Pipeline,
        valid_stage: ValidationStage,
    ):
        """Сообщения без device_id должны отсеиваться."""
        pipeline.add_stage(valid_stage)
        await pipeline.setup()

        msg = Message(device_id='', payload={"value": 1})
        with not_raises(Exception):
            result = await pipeline.execute(msg)

        assert result is None
        assert 'reject_reason' in msg.metadata
        assert 'reject_stage' in msg.metadata
        assert msg.metadata['reject_stage'] == valid_stage.name
        assert pipeline.stats.get('filtered', -1) == 1

    @pytest.mark.asyncio
    async def test_filter_empty(
        self,
        pipeline: Pipeline,
        valid_stage: ValidationStage
    ):
        """Пустые (без нагрузки) сообщения должны отсеиваться."""
        pipeline.add_stage(valid_stage)
        await pipeline.setup()

        msg = Message(device_id="dev-1", payload={})
        with not_raises(Exception):
            result = await pipeline.execute(msg)

        assert result is None
        assert 'reject_reason' in msg.metadata
        assert 'reject_stage' in msg.metadata
        assert msg.metadata['reject_stage'] == valid_stage.name
        assert pipeline._filtered_count == 1


class TestAuthorizationStage:
    """Тесты для этапа проверки авторизации."""

    @pytest.mark.asyncio
    async def test_authed_passes(
        self,
        pipeline: Pipeline,
        auth_stage: AuthorizationStage,
        telemetry_message: Message,
        device: Device
    ):
        """Сообщения от зарегистрированного девайса должны проходить."""
        pipeline.add_stage(auth_stage)
        await pipeline.setup()

        with not_raises(Exception):
            await auth_stage._registry.register(device)
            result = await pipeline.execute(telemetry_message)

        assert result is not None
        assert result.processed is True
        assert pipeline.stats.get('processed', -1) == 1

    @pytest.mark.asyncio
    async def test_auth_wo_register(
        self,
        pipeline: Pipeline,
        auth_stage: AuthorizationStage
    ):
        """Сообщения от незарегистрированного device_id должны отсеиваться."""
        pipeline.add_stage(auth_stage)
        await pipeline.setup()

        msg = Message(device_id="UNAUTH", payload={"value": 1})
        with not_raises(Exception):
            result = await pipeline.execute(msg)

        assert result is None
        assert 'reject_reason' in msg.metadata
        assert 'reject_stage' in msg.metadata
        assert msg.metadata['reject_stage'] == auth_stage.name
        assert pipeline.stats.get('filtered', -1) == 1

    @pytest.mark.asyncio
    async def test_auth_error_status(
        self,
        pipeline: Pipeline,
        auth_stage: AuthorizationStage,
        telemetry_message: Message,
        device: Device
    ):
        """Сообщения от девайса с ошибкой фильтруются."""
        pipeline.add_stage(auth_stage)
        await pipeline.setup()

        device.device_id = 'ERR_STATUS'
        device.device_status = DeviceStatus.ERROR
        await auth_stage._registry.register(device)

        result = await pipeline.execute(telemetry_message)

        assert result is None
        assert 'reject_reason' in telemetry_message.metadata
        assert 'reject_stage' in telemetry_message.metadata
        assert telemetry_message.metadata['reject_stage'] == auth_stage.name
        assert pipeline.stats.get('filtered', -1) == 1


class TestCleanupStage:
    """Тесты для этапа очистки некорректных значений."""

    @pytest.mark.asyncio
    async def test_cleanup_correct_passes(
        self,
        pipeline: Pipeline,
        cleanup_stage: CleanupStage,
        telemetry_message: Message
    ):
        """Сообщения с корректными значениями проходят."""
        pipeline.add_stage(cleanup_stage)
        await pipeline.setup()

        result = await pipeline.execute(telemetry_message)

        assert result is not None
        assert result.processed is True
        assert pipeline.stats["processed"] == 1

    @pytest.mark.asyncio
    async def test_cleanup_float_full(
        self,
        pipeline: Pipeline,
        cleanup_stage: CleanupStage
    ):
        """Если все поля в нагрузке некорректны, сообщение фильтруется."""
        pipeline.add_stage(cleanup_stage)
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
        assert 'reject_reason' in msg.metadata
        assert 'reject_stage' in msg.metadata
        assert msg.metadata['reject_stage'] == cleanup_stage.name
        assert pipeline.stats["filtered"] == 1

    @pytest.mark.asyncio
    async def test_cleanup_float_partial(
        self,
        pipeline: Pipeline,
        cleanup_stage: CleanupStage
    ):
        """Если часть нагрузки некорректна, остальное сохраняется."""
        pipeline.add_stage(cleanup_stage)
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
