import asyncio
from fnmatch import fnmatch
from dataclasses import dataclass
from models.message import Message
from typing import Any, Callable, Coroutine


@dataclass
class Subscription:
    handler: Callable[[Message], Coroutine[Any, Any, None]]
    mes_type: str
    priority: int = 0

    def matches(self, topic: str) -> bool:
        return fnmatch(topic, self.mes_type)


class MessageBus:
    def __init__(self, max_queue: int = 10000):
        self.queue: asyncio.Queue[tuple[str, Message]] = asyncio.Queue(
            maxsize=max_queue
        )
        self.subscriptions: list[Subscription] = []
        self.running = False
        self.task: asyncio.Task | None = None

        self.published_count = 0
        self.delivered_count = 0
        self.error_count = 0

    @property
    def stats(self) -> dict[str, int]:
        return {
            "published": self.published_count,
            "delivered": self.delivered_count,
            "errors": self.error_count,
            "queue_size": self.queue.qsize(),
            "subscribers": len(self.subscriptions),
        }

    def subscribe(
        self,
        mes_type: str,
        handler: Callable[[Message], Coroutine[Any, Any, None]],
        priority: int = 0,
    ) -> Subscription:
        sub = Subscription(
            mes_type=mes_type,
            handler=handler,
            priority=priority,
        )
        self.subscriptions.append(sub)
        self.subscriptions.sort(key=lambda s: s.priority, reverse=True)
        print(f"Added subscriber on topic {mes_type}, priority={priority})")
        return sub

    def unsubscribe(self, subscription: Subscription) -> None:
        self.subscriptions.remove(subscription)

    async def publish(self, mes_type: str, message: Message) -> None:
        await self.queue.put((mes_type, message))
        self.published_count += 1

    def publish_nowait(self, mes_type, message: Message) -> None:
        self.queue.put_nowait((mes_type, message))
        self.published_count += 1

    async def dispatch(self, mes_type: str, message: Message):
        matched = False
        for sub in self.subscriptions:
            if sub.matches(mes_type):
                matched = True
                try:
                    await sub.handler(message)
                    self.delivered_count += 1
                except Exception:
                    print(
                        f"Handler error on topic '{mes_type}'"
                    )
                    self.error_count += 1

        if not matched:
            print(f"No subscribers for topic '{mes_type}'")

    async def process_queue(self):
        while self.running:
            try:
                type, message = await asyncio.wait_for(
                    self.queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            if type is None:
                break
            await self.dispatch(type, message)

    async def start(self):
        if self.running:
            return
        self.running = True
        self.task = asyncio.create_task(self.process_queue())
        print('Bus started')

    async def stop(self):
        self.running = False
        if self.task:
            await self.queue.put((None, None))
            await self.task
            self.task = None
        print(
            f"MessageBus stopped. "
            f"Published={self.published_count} "
            f"Delivered={self.delivered_count} "
            f"Errors={self.error_count}"
        )
