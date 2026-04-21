"""Тест модуля шины сообщений."""
import pytest
import asyncio
from unittest.mock import AsyncMock
from config.topics import TopicManager, TopicKey
from core.message_bus import MessageBus
from models.message import Message
from tests.conftest import (
    not_raises, drain, BUS_MAX_QUEUE
)


class TestDeliver:
    """Базовая доставка сообщений."""

    @pytest.mark.asyncio
    async def test_deliver(
        self,
        topics: TopicManager,
        running_bus: MessageBus,
        telemetry_message: Message
    ):
        """Сообщение доходит до подписчика."""
        handler = AsyncMock()
        running_bus.subscribe(
            topics.get_subscription_pattern(
                TopicKey.DEVICES_TELEMETRY
            ),
            handler
        )

        await running_bus.publish(
            topics.get(
                TopicKey.DEVICES_TELEMETRY,
                device_id=telemetry_message.device_id
            ),
            telemetry_message
        )
        with not_raises(Exception):
            await drain(running_bus)

        handler.assert_awaited_once_with(telemetry_message)

    @pytest.mark.asyncio
    async def test_no_subscribers_no_crash(
        self,
        topics: TopicManager,
        running_bus: MessageBus,
        telemetry_message: Message
    ):
        """Если нет подписчиков на тему, шина не ломается."""
        await running_bus.publish(
            topics.get(
                TopicKey.DEVICES_TELEMETRY,
                device_id=telemetry_message.device_id
            ),
            telemetry_message
        )
        with not_raises(Exception):
            await drain(running_bus)

        assert running_bus._published_count == 1
        assert running_bus._delivered_count == 0
        assert running_bus._error_count == 0

    @pytest.mark.asyncio
    async def test_multiple_subscribers_all_called(
        self,
        topics: TopicManager,
        running_bus: MessageBus,
        telemetry_message: Message
    ):
        """Если несколько подписчиков, то вызываются все."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        running_bus.subscribe(
            topics.get_subscription_pattern(
                TopicKey.DEVICES_TELEMETRY
            ),
            handler1
        )
        running_bus.subscribe(
            topics.get_subscription_pattern(
                TopicKey.DEVICES_TELEMETRY
            ),
            handler2
        )

        await running_bus.publish(
            topics.get(
                TopicKey.DEVICES_TELEMETRY,
                device_id=telemetry_message.device_id
            ),
            telemetry_message
        )
        with not_raises(Exception):
            await drain(running_bus)

        handler1.assert_awaited_once_with(telemetry_message)
        handler2.assert_awaited_once_with(telemetry_message)

    @pytest.mark.asyncio
    async def test_delivered_count_per_subscriber(
        self,
        topics: TopicManager,
        running_bus: MessageBus,
        telemetry_message: Message
    ):
        """Если несколько подписчиков, то доставлено всем."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        running_bus.subscribe(
            topics.get_subscription_pattern(
                TopicKey.DEVICES_TELEMETRY
            ),
            handler1
        )
        running_bus.subscribe(
            topics.get_subscription_pattern(
                TopicKey.DEVICES_TELEMETRY
            ),
            handler2
        )

        await running_bus.publish(
            topics.get(
                TopicKey.DEVICES_TELEMETRY,
                device_id=telemetry_message.device_id
            ),
            telemetry_message
        )
        with not_raises(Exception):
            await drain(running_bus)

        assert running_bus._delivered_count == 2


class TestWildcard:
    """Совпадение топиков по wildcard."""

    @pytest.mark.asyncio
    async def test_wildcard_match(
        self,
        topics: TopicManager,
        running_bus: MessageBus,
        telemetry_message: Message
    ):
        """Топик с wildcard совпадает."""
        handler = AsyncMock()
        running_bus.subscribe(
            topics.get_subscription_pattern(
                TopicKey.DEVICES_TELEMETRY
            ),
            handler
        )

        await running_bus.publish(
            topics.get(
                TopicKey.DEVICES_TELEMETRY,
                device_id=telemetry_message.device_id
            ),
            telemetry_message
        )
        with not_raises(Exception):
            await drain(running_bus)

        handler.assert_awaited_once_with(telemetry_message)

    @pytest.mark.asyncio
    async def test_wrong_wild_prefix(
        self,
        topics: TopicManager,
        running_bus: MessageBus,
        telemetry_message: Message
    ):
        """processed.telemetry.* не совпадает с telemetry.*."""
        handler = AsyncMock()
        running_bus.subscribe(
            topics.get_subscription_pattern(
                TopicKey.PROCESSED_TELEMETRY
            ),
            handler
        )

        await running_bus.publish(
            topics.get(
                TopicKey.DEVICES_TELEMETRY,
                device_id=telemetry_message.device_id
            ),
            telemetry_message
        )
        with not_raises(Exception):
            await drain(running_bus)

        handler.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_exact_match_without_wildcard(
        self,
        topics: TopicManager,
        running_bus: MessageBus,
        telemetry_message: Message
    ):
        """Если тема точно совпадает без *, то проходит."""
        handler = AsyncMock()
        running_bus.subscribe(
            topics.get(
                TopicKey.DEVICES_TELEMETRY,
                device_id=telemetry_message.device_id
            ),
            handler
        )

        await running_bus.publish(
            topics.get(
                TopicKey.DEVICES_TELEMETRY,
                device_id=telemetry_message.device_id
            ),
            telemetry_message
        )
        with not_raises(Exception):
            await drain(running_bus)

        handler.assert_awaited_once_with(telemetry_message)


class TestPriority:
    """Порядок вызова по приоритету."""

    @pytest.mark.asyncio
    async def test_priority_order(
        self,
        topics: TopicManager,
        running_bus: MessageBus,
        telemetry_message: Message
    ):
        """Подписчик с высоким приоритетом вызывается первым."""
        call_order = []

        async def _low(msg):
            """Обработчик подписчика с низким приоритетом."""
            call_order.append('low')

        async def _high(msg):
            """Обработчик подписчика с высоким приоритетом."""
            call_order.append('high')

        running_bus.subscribe(
            topics.get_subscription_pattern(TopicKey.DEVICES_TELEMETRY),
            _low,
            priority=0
        )
        running_bus.subscribe(
            topics.get_subscription_pattern(TopicKey.DEVICES_TELEMETRY),
            _high,
            priority=10
        )

        await running_bus.publish(
            topics.get(
                TopicKey.DEVICES_TELEMETRY,
                device_id=telemetry_message.device_id
            ),
            telemetry_message
        )
        with not_raises(Exception):
            await drain(running_bus)

        assert call_order == ["high", "low"]

    @pytest.mark.asyncio
    async def test_equal_priority_fifo(
        self,
        topics: TopicManager,
        running_bus: MessageBus,
        telemetry_message: Message
    ):
        """Подписчики с одним приоритетом вызываются в порядке добавления."""
        call_order = []

        async def _first(msg):
            """Обработчик первого подписчика."""
            call_order.append('first')

        async def _second(msg):
            """Обработчик второго подписчика."""
            call_order.append('second')

        running_bus.subscribe(
            topics.get_subscription_pattern(TopicKey.DEVICES_TELEMETRY),
            _first,
            priority=10
        )
        running_bus.subscribe(
            topics.get_subscription_pattern(TopicKey.DEVICES_TELEMETRY),
            _second,
            priority=10
        )

        await running_bus.publish(
            topics.get(
                TopicKey.DEVICES_TELEMETRY,
                device_id=telemetry_message.device_id
            ),
            telemetry_message
        )
        with not_raises(Exception):
            await drain(running_bus)

        assert call_order == ["first", "second"]


class TestSubscribeUnsubscribe:
    """Управление подписками."""

    @pytest.mark.asyncio
    async def test_unsubscribe_stops_delivery(
        self,
        topics: TopicManager,
        running_bus: MessageBus,
        telemetry_message: Message
    ):
        """Отписка от топика отменяет доставку подписчику."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        sub = running_bus.subscribe(
            topics.get_subscription_pattern(TopicKey.DEVICES_TELEMETRY),
            handler1
        )
        running_bus.subscribe(
            topics.get_subscription_pattern(TopicKey.DEVICES_TELEMETRY),
            handler2
        )

        running_bus.unsubscribe(sub)

        await running_bus.publish(
            topics.get(
                TopicKey.DEVICES_TELEMETRY,
                device_id=telemetry_message.device_id
            ),
            telemetry_message
        )
        with not_raises(Exception):
            await drain(running_bus)

        handler1.assert_not_awaited()
        handler2.assert_awaited_once_with(telemetry_message)

    @pytest.mark.asyncio
    async def test_unsubscribe_from_removes_all(
        self,
        topics: TopicManager,
        running_bus: MessageBus,
        telemetry_message: Message
    ):
        """Отписка от темы отменяет доставку всем подписчикам на нее."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        running_bus.subscribe(
            topics.get_subscription_pattern(TopicKey.DEVICES_TELEMETRY),
            handler1
        )
        running_bus.subscribe(
            topics.get_subscription_pattern(TopicKey.DEVICES_TELEMETRY),
            handler2
        )

        running_bus.unsubscribe_from(
            topics.get_subscription_pattern(TopicKey.DEVICES_TELEMETRY)
        )

        await running_bus.publish(
            topics.get(
                TopicKey.DEVICES_TELEMETRY,
                device_id=telemetry_message.device_id
            ),
            telemetry_message
        )
        with not_raises(Exception):
            await drain(running_bus)

        handler1.assert_not_awaited()
        handler2.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unsubscribe_unknown_no_crash(
        self,
        topics: TopicManager,
        running_bus: MessageBus,
        telemetry_message: Message
    ):
        """Отписка от неизвестной темы не ломает шину."""
        handler = AsyncMock()
        running_bus.subscribe(
            topics.get_subscription_pattern(TopicKey.DEVICES_TELEMETRY),
            handler
        )

        running_bus.unsubscribe_from('some_topic')

        await running_bus.publish(
            topics.get(
                TopicKey.DEVICES_TELEMETRY,
                device_id=telemetry_message.device_id
            ),
            telemetry_message
        )
        with not_raises(Exception):
            await drain(running_bus)

        handler.assert_awaited_once_with(telemetry_message)


class TestPublish:
    """Методы публикации."""

    @pytest.mark.asyncio
    async def test_publish_ok(
        self,
        topics: TopicManager,
        running_bus: MessageBus,
        telemetry_message: Message
    ):
        """Сообщение публикуется в свободную очередь."""
        with not_raises(Exception):
            await running_bus.publish(
                topics.get(
                    TopicKey.DEVICES_TELEMETRY,
                    device_id=telemetry_message.device_id
                ),
                telemetry_message
            )
            assert running_bus._queue.qsize() == 1
            topic, msg = running_bus._queue.get_nowait()
        assert topic == topics.get(
            TopicKey.DEVICES_TELEMETRY,
            device_id=telemetry_message.device_id
        )
        assert msg == telemetry_message
        assert running_bus._published_count == 1

    @pytest.mark.asyncio
    async def test_publish_full_queue(
        self,
        topics: TopicManager,
        running_bus: MessageBus,
        telemetry_message: Message
    ):
        """Если очередь заполнена, то ждет, пока обработается."""
        with not_raises(Exception):
            for i in range(BUS_MAX_QUEUE):
                await running_bus.publish(
                    topics.get(
                        TopicKey.DEVICES_TELEMETRY,
                        device_id=telemetry_message.device_id
                    ),
                    telemetry_message
                )
            assert running_bus._queue.qsize() == BUS_MAX_QUEUE
        with not_raises(Exception):
            await running_bus.publish(
                topics.get(
                    TopicKey.DEVICES_TELEMETRY,
                    device_id=telemetry_message.device_id
                ),
                telemetry_message
            )

    @pytest.mark.asyncio
    async def test_publish_nowait_ok(
        self,
        topics: TopicManager,
        running_bus: MessageBus,
        telemetry_message: Message
    ):
        """Сообщение публикуется в свободную очередь."""
        with not_raises(Exception):
            await running_bus.publish_nowait(
                topics.get(
                    TopicKey.DEVICES_TELEMETRY,
                    device_id=telemetry_message.device_id
                ),
                telemetry_message
            )
            assert running_bus._queue.qsize() == 1
            topic, msg = running_bus._queue.get_nowait()
        assert topic == topics.get(
            TopicKey.DEVICES_TELEMETRY,
            device_id=telemetry_message.device_id
        )
        assert msg == telemetry_message
        assert running_bus._published_count == 1

    @pytest.mark.asyncio
    async def test_publish_nowait_full_queue_raises(
        self,
        topics: TopicManager,
        running_bus: MessageBus,
        telemetry_message: Message
    ):
        """Если очередь заполнена, возникает исключение."""
        max_len = running_bus._queue.maxsize
        with not_raises(Exception):
            for i in range(max_len):
                await running_bus.publish_nowait(
                    topics.get(
                        TopicKey.DEVICES_TELEMETRY,
                        device_id=telemetry_message.device_id
                    ),
                    telemetry_message
                )
            assert running_bus._queue.qsize() == max_len
        with pytest.raises(asyncio.QueueFull):
            await running_bus.publish_nowait(
                topics.get(
                    TopicKey.DEVICES_TELEMETRY,
                    telemetry_message.device_id
                ),
                telemetry_message
            )


class TestStats:
    """Статистика шины."""

    @pytest.mark.asyncio
    async def test_stats_on_success(
        self,
        topics: TopicManager,
        running_bus: MessageBus,
        telemetry_message: Message
    ):
        """Статистика после успешной доставки."""
        handler = AsyncMock()
        running_bus.subscribe(
            topics.get_subscription_pattern(TopicKey.DEVICES_TELEMETRY),
            handler
        )

        await running_bus.publish(
            topics.get(
                TopicKey.DEVICES_TELEMETRY,
                device_id=telemetry_message.device_id
            ),
            telemetry_message
        )
        with not_raises(Exception):
            await drain(running_bus)

        stats = running_bus.stats
        assert int(stats.get('published', -1)) == 1
        assert int(stats.get('delivered', -1)) == 1
        assert int(stats.get('errors', -1)) == 0
        assert int(stats.get('queue_size', -1)) == 0
        assert int(stats.get('subscribers', -1)) == 1

    @pytest.mark.asyncio
    async def test_error_count_on_handler_exception(
        self,
        topics: TopicManager,
        running_bus: MessageBus,
        telemetry_message: Message
    ):
        """Статистика после ошибки обработчика."""

        def _handler(msg: Message):
            """Тестовый поломанный обработчик."""
            raise ValueError('Test handler error')

        running_bus.subscribe(
            topics.get_subscription_pattern(TopicKey.DEVICES_TELEMETRY),
            _handler
        )

        await running_bus.publish(
            topics.get(
                TopicKey.DEVICES_TELEMETRY,
                device_id=telemetry_message.device_id
            ),
            telemetry_message
        )
        with not_raises(Exception):
            await drain(running_bus)

        stats = running_bus.stats
        assert int(stats.get('published', -1)) == 1
        assert int(stats.get('delivered', -1)) == 0
        assert int(stats.get('errors', -1)) == 1
        assert int(stats.get('queue_size', -1)) == 0
        assert int(stats.get('subscribers', -1)) == 1

    @pytest.mark.asyncio
    async def test_stats_subscribers_count(
        self,
        topics: TopicManager,
        running_bus: MessageBus,
        telemetry_message: Message
    ):
        """Количество подписчиков в подписке соответствует."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        running_bus.subscribe(
            topics.get_subscription_pattern(TopicKey.DEVICES_TELEMETRY),
            handler1
        )
        running_bus.subscribe(
            topics.get_subscription_pattern(TopicKey.DEVICES_TELEMETRY),
            handler2
        )

        await running_bus.publish(
            topics.get(
                TopicKey.DEVICES_TELEMETRY,
                device_id=telemetry_message.device_id
            ),
            telemetry_message
        )
        with not_raises(Exception):
            await drain(running_bus)

        stats = running_bus.stats
        assert int(stats.get('published', -1)) == 1
        assert int(stats.get('delivered', -1)) == 2
        assert int(stats.get('errors', -1)) == 0
        assert int(stats.get('queue_size', -1)) == 0
        assert int(stats.get('subscribers', -1)) == 2

    @pytest.mark.asyncio
    async def test_stats_queue_size(
        self,
        topics: TopicManager,
        running_bus: MessageBus
    ):
        """Количество подписчиков в подписке соответствует."""
        handler = AsyncMock()
        with not_raises(Exception):
            for i in range(5):
                running_bus.subscribe(
                    topics.get_subscription_pattern(
                        TopicKey.DEVICES_TELEMETRY
                    ),
                    handler
                )
        stats = running_bus.stats
        assert int(stats.get('published', -1)) == 0
        assert int(stats.get('delivered', -1)) == 0
        assert int(stats.get('errors', -1)) == 0
        assert int(stats.get('queue_size', -1)) == 0
        assert int(stats.get('subscribers', -1)) == 5


class TestLifecycle:
    """Жизненный цикл шины."""

    @pytest.mark.asyncio
    async def test_double_start_ignored(
        self,
        running_bus: MessageBus
    ):
        """Повторный старт ничего не делает."""
        with not_raises(Exception):
            await running_bus.start()
            task1 = running_bus._task
            await running_bus.start()
            task2 = running_bus._task
            assert task1 is task2

    @pytest.mark.asyncio
    async def test_stop_before_start_no_crash(
        self,
        running_bus: MessageBus
    ):
        """Остановка до запуска не приводит к ошибке."""
        with not_raises(Exception):
            await running_bus.stop()
