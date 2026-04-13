"""Тест модуля конвейера обработки сообщений."""
import pytest
from unittest.mock import AsyncMock
from core.pipeline.pipeline import Pipeline
from core.pipeline.stages import PipelineStage
from models.message import Message
from tests.conftest import not_raises


class PassThroughStage(PipelineStage):
    """Проходная стадия, ничего не делает с сообщением."""

    name = "passthrough"

    async def process(self, message: Message):
        """Обработка сообщений."""
        return message


class FilterStage(PipelineStage):
    """Полный фильтр сообщений."""

    name = "filter"

    async def process(self, message: Message):
        """Обработка сообщений."""
        return None


@pytest.fixture(scope='module')
def pass_stage():
    """Проходная стадия."""
    return PassThroughStage()


@pytest.fixture(scope='module')
def filter_stage():
    """Фильтрующая все стадия."""
    return FilterStage()


class TestAddStage:
    """Тестирование добавления этапа."""

    @pytest.mark.asyncio
    async def test_add_stage(
        self,
        pipeline: Pipeline,
        pass_stage: PipelineStage
    ):
        """Стадия обработки успешно добавляется."""
        with not_raises(Exception):
            pipeline.add_stage(pass_stage)
        assert pipeline.stages == [pass_stage.name]

    @pytest.mark.asyncio
    async def test_add_stage_count(
        self,
        pipeline: Pipeline,
        pass_stage: PipelineStage
    ):
        """При добавлении увеличивается число стадий."""
        with not_raises(Exception):
            pipeline.add_stage(pass_stage)
        stats = pipeline.stats
        assert stats.get('stages', -1) == 1


class TestRemoveStage:
    """Тестирование удаления этапа."""

    @pytest.mark.asyncio
    async def test_remove_stage(
        self,
        pipeline: Pipeline,
        pass_stage: PipelineStage,
        filter_stage: PipelineStage
    ):
        """Стадия обработки успешно удаляется."""
        pipeline.add_stage(pass_stage)
        pipeline.add_stage(filter_stage)
        with not_raises(Exception):
            pipeline.remove_stage(pass_stage.name)
        assert pipeline.stages == [filter_stage.name]

    @pytest.mark.asyncio
    async def test_remove_unknown_stage(
        self,
        pipeline: Pipeline,
        pass_stage: PipelineStage
    ):
        """При попытке удалить неизвестную стадию ничего не ломается."""
        pipeline.add_stage(pass_stage)
        with not_raises(Exception):
            pipeline.remove_stage('unknown')
        assert pipeline.stages == [pass_stage.name]

    @pytest.mark.asyncio
    async def test_remove_double_stages(
        self,
        pipeline: Pipeline,
        pass_stage: PipelineStage
    ):
        """Удаляются все вхождения стадии в конвейер."""
        pipeline.add_stage(pass_stage)
        pipeline.add_stage(pass_stage)
        with not_raises(Exception):
            pipeline.remove_stage(pass_stage.name)
        assert pipeline.stages == []

    @pytest.mark.asyncio
    async def test_remove_count(
        self,
        pipeline: Pipeline,
        pass_stage: PipelineStage
    ):
        """Удаление стадии изменяет счетчик."""
        pipeline.add_stage(pass_stage)
        with not_raises(Exception):
            pipeline.remove_stage(pass_stage.name)
        stats = pipeline.stats
        assert stats.get('stages', -1) == 0


class TestProperties:
    """Тесты для свойств конвейера."""

    @pytest.mark.asyncio
    async def test_stats_on_ready(
        self,
        pipeline: Pipeline
    ):
        """При инициализации конвейера все статы по 0."""
        stats = pipeline.stats
        assert stats.get('stages', -1) == 0
        assert stats.get('processed', -1) == 0
        assert stats.get('filtered', -1) == 0
        assert stats.get('errors', -1) == 0

    @pytest.mark.asyncio
    async def test_stats_change(
        self,
        pipeline: Pipeline,
        pass_stage: PipelineStage,
        filter_stage: PipelineStage,
        telemetry_message: Message
    ):
        """При работе конвейера статистика изменяется соответственно."""
        pipeline.add_stage(pass_stage)
        with not_raises(Exception):
            await pipeline.setup()
            await pipeline.execute(telemetry_message)
        assert pipeline.stats.get('stages', -1) == 1
        assert pipeline.stats.get('processed', -1) == 1
        assert pipeline.stats.get('filtered', -1) == 0
        assert pipeline.stats.get('errors', -1) == 0
        await pipeline.teardown()
        with not_raises(Exception):
            pipeline.add_stage(filter_stage)
            await pipeline.setup()
            await pipeline.execute(telemetry_message)
        assert pipeline.stats.get('stages', -1) == 2
        assert pipeline.stats.get('processed', -1) == 1
        assert pipeline.stats.get('filtered', -1) == 1
        assert pipeline.stats.get('errors', -1) == 0

    @pytest.mark.asyncio
    async def test_stages_on_ready(
        self,
        pipeline: Pipeline
    ):
        """При инициализации конвейера список этапов пустой."""
        stages = pipeline.stages
        assert stages == []


class TestSetup:
    """Тест запуска конвейера."""

    @pytest.mark.asyncio
    async def test_setup_awaits_all(
        self,
        pipeline: Pipeline
    ):
        """При подготовке конвейера подготавливаются все его стадии."""
        stage1 = AsyncMock()
        stage1.setup = AsyncMock()

        stage2 = AsyncMock()
        stage2.setup = AsyncMock()

        with not_raises(Exception):
            pipeline.add_stage(stage1)
            pipeline.add_stage(stage2)

            await pipeline.setup()

        stage1.setup.assert_awaited_once()
        stage2.setup.assert_awaited_once()


class TestTeardown:
    """Тесты выключения конвейера."""

    @pytest.mark.asyncio
    async def test_teardown_awaits_all(
        self,
        pipeline: Pipeline
    ):
        """При выключении конвейера выключаются все его стадии."""
        stage1 = AsyncMock()
        stage1.teardown = AsyncMock()

        stage2 = AsyncMock()
        stage2.teardown == AsyncMock()

        with not_raises(Exception):
            pipeline.add_stage(stage1)
            pipeline.add_stage(stage2)

            await pipeline.setup()
            await pipeline.teardown()

        stage1.teardown.assert_awaited_once()
        stage2.teardown.assert_awaited_once()


class TestExecute:
    """Тесты обработки сообщения на конвейере."""

    @pytest.mark.asyncio
    async def test_execute_zero_stages(
        self,
        pipeline: Pipeline,
        telemetry_message: Message
    ):
        """Если запустить без этапов, помечет как обработанное и вернет."""
        await pipeline.setup()
        with not_raises(Exception):
            result = await pipeline.execute(telemetry_message)
        assert pipeline._processed_count == 1
        assert result is not None
        assert result is telemetry_message
        assert result.processed is True

    @pytest.mark.asyncio
    async def test_execute_passthrough(
        self,
        pipeline: Pipeline,
        pass_stage: PipelineStage,
        telemetry_message: Message
    ):
        """Сообщение успешно проходит одну стадию."""
        pipeline.add_stage(pass_stage)
        await pipeline.setup()
        with not_raises(Exception):
            result = await pipeline.execute(telemetry_message)
        assert pipeline._processed_count == 1
        assert result is not None
        assert result is telemetry_message
        assert result.processed is True

    @pytest.mark.asyncio
    async def test_execute_multiple(
        self,
        pipeline: Pipeline,
        pass_stage: PipelineStage,
        telemetry_message: Message
    ):
        """Количество стадий не влияет на выход."""
        pipeline.add_stage(pass_stage)
        pipeline.add_stage(pass_stage)
        await pipeline.setup()
        with not_raises(Exception):
            result = await pipeline.execute(telemetry_message)
        assert pipeline._processed_count == 1
        assert result is not None
        assert result is telemetry_message
        assert result.processed is True

    @pytest.mark.asyncio
    async def test_execute_stage_order(
        self,
        pipeline: Pipeline,
        telemetry_message: Message
    ):
        """Этапы выполняются в порядке добавления."""
        order = []

        class FirstStage(PipelineStage):
            """Первая стадия конвейера."""

            name = "first_stage"

            async def process(self, msg: Message):
                """Обработка стадии."""
                order.append("first")
                return msg

        class SecondStage(PipelineStage):
            """Вторая стадия конвейера."""

            name = "second"

            async def process(self, msg: Message):
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
    async def test_stage_error_count(
        self,
        pipeline: Pipeline,
        telemetry_message: Message
    ):
        """Ошибка обработки не ломает все и добавляет счетчик."""
        class BrokenStage(PipelineStage):
            """Сломанный этап конвейера."""

            name = "broken"

            async def process(self, msg):
                """Обработка стадии."""
                raise ValueError("Test stage fail")

        pipeline.add_stage(BrokenStage())
        await pipeline.setup()
        with not_raises(Exception):
            await pipeline.execute(telemetry_message)

        assert pipeline.stats.get('errors', -1) == 1

    @pytest.mark.asyncio
    async def test_execute_filter(
        self,
        pipeline: Pipeline,
        filter_stage: PipelineStage,
        telemetry_message: Message
    ):
        """При фильтрации сообщения ничего не ломается и плюс в счетчик."""
        pipeline.add_stage(filter_stage)
        await pipeline.setup()
        with not_raises(Exception):
            result = await pipeline.execute(telemetry_message)
        assert result is None
        assert pipeline.stats.get('filtered', -1) == 1

    @pytest.mark.asyncio
    async def test_execute_awaits_process(
        self,
        pipeline: Pipeline,
        telemetry_message: Message
    ):
        """При вызове execute() для всех этапов ожидается process."""
        stage1 = AsyncMock()
        stage1.process = AsyncMock()

        stage2 = AsyncMock()
        stage2.process == AsyncMock()

        with not_raises(Exception):
            pipeline.add_stage(stage1)
            pipeline.add_stage(stage2)

            await pipeline.setup()
            await pipeline.execute(telemetry_message)
            await pipeline.teardown()

        stage1.process.assert_awaited_once()
        stage2.process.assert_awaited_once()
