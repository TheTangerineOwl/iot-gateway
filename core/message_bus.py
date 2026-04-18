"""Шина сообщений для взаимодействия."""
import asyncio
from fnmatch import fnmatch
from dataclasses import dataclass
import logging
from models.message import Message
from typing import Any, Callable, Coroutine
from config.config import get_conf, YAMLConfigLoader


logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    """Подписка на тему сообщения."""

    handler: Callable[[Message], Coroutine[Any, Any, None]]
    mes_topic: str
    priority: int = 0

    def matches(self, topic: str) -> bool:
        """
        Проверка темы сообщения.

        Проверяет, соответствует ли тема сообщению заданной теме подписки
        с поддержкой wildcard (* в теме).
        """
        return fnmatch(topic, self.mes_topic)


class MessageBus:
    """Шина сообщений для взаимодействия модулей."""

    def __init__(self, config: YAMLConfigLoader):
        """Шина сообщений."""
        self._config = config
        self._queue: asyncio.Queue[tuple[str, Message]] = asyncio.Queue(
            maxsize=int(get_conf(
                self._config,
                'gateway.message_bus.max_queue',
                10000
            ))
        )
        self._subscriptions: list[Subscription] = []
        self._running = False
        self._task: asyncio.Task | None = None

        self._published_count = 0
        self._delivered_count = 0
        self._error_count = 0

    @property
    def stats(self) -> dict[str, int]:
        """Статистика работы шины сообщений."""
        return {
            "published": self._published_count,
            "delivered": self._delivered_count,
            "errors": self._error_count,
            "queue_size": self._queue.qsize(),
            "subscribers": len(self._subscriptions),
        }

    def subscribe(
        self,
        mes_topic: str,
        handler: Callable[[Message], Coroutine[Any, Any, None]],
        priority: int = 0,
    ) -> Subscription:
        """Добавить обработчик на сообщения с заданной темой."""
        sub = Subscription(
            mes_topic=mes_topic,
            handler=handler,
            priority=priority,
        )
        self._subscriptions.append(sub)
        self._subscriptions.sort(key=lambda s: s.priority, reverse=True)
        logger.debug(
            "Added subscriber on topic '%s', priority=%d",
            mes_topic, priority
        )
        return sub

    def unsubscribe(self, subscription: Subscription) -> None:
        """Удалить обработчик сообщений с заданной темой."""
        try:
            self._subscriptions.remove(subscription)
        except ValueError:
            pass

    def unsubscribe_from(self, topic: str) -> None:
        """Удалить все обработчики сообщений для заданной темы."""
        for sub in reversed(self._subscriptions):
            if sub.matches(topic):
                self._subscriptions.remove(sub)

    async def publish(self, mes_topic: str, message: Message) -> None:
        """Поместить сообщение в очередь."""
        await self._queue.put((mes_topic, message))
        self._published_count += 1

    async def publish_nowait(self, mes_topic: str, message: Message) -> None:
        """Поместить сообщение в очередь (ошибка, если очередь полна)."""
        self._queue.put_nowait((mes_topic, message))
        self._published_count += 1

    async def _dispatch(self, mes_topic: str, message: Message):
        """Передать сообщение подписчикам."""
        matched = False
        for sub in self._subscriptions:
            if sub.matches(mes_topic):
                matched = True
                try:
                    await sub.handler(message)
                    self._delivered_count += 1
                except Exception as ex:
                    logger.error(
                        "Handler error on topic '%s': %s",
                        mes_topic, ex, exc_info=True
                    )
                    self._error_count += 1

        if not matched:
            logger.warning("No subscribers for topic '%s'", mes_topic)

    async def _process_queue(self):
        """Обработать очередь сообщений."""
        while self._running:
            try:
                topic, message = await asyncio.wait_for(
                    self._queue.get(),
                    # timeout=env.float('MESQ_TIMEOUT', default=1.0)
                    timeout=float(get_conf(
                        self._config,
                        'gateway.message_bus.timeout',
                        1.0
                    ))
                )
            except asyncio.TimeoutError:
                continue
            if topic is None:
                break
            await self._dispatch(topic, message)

    async def start(self):
        """Запуск шины сообщений."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._process_queue())
        logger.debug('Bus started')

    async def stop(self):
        """Остановка шины сообщений и вывод статистики."""
        self._running = False
        if self._task:
            await self._queue.put((None, None))
            await self._task
            self._task = None
        logger.info(
            "MessageBus stopped. "
            "Published = %d "
            "Delivered = %d "
            "Errors = %d",
            self._published_count,
            self._delivered_count,
            self._error_count
        )
