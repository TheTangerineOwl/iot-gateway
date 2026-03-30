import asyncio
from models.message import Message


class MessageBus:
    def __init__(self, max_queue: int = 10000):
        self.queue: asyncio.Queue[Message] = asyncio.Queue(
            maxsize=max_queue
        )
        self.running = False
        self.task: asyncio.Task | None = None

        self.published_count = 0
        self.delivered_count = 0
        self.error_count = 0

    async def publish(self, message: Message) -> None:
        await self.queue.put(message)
        self.published_count += 1

    def publish_nowait(self, message: Message) -> None:
        self.queue.put_nowait(message)
        self.published_count += 1

    async def dispatch(self, message: Message):
        pass

    async def process_queue(self):
        while self.running:
            try:
                message = await asyncio.wait_for(
                    self.queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            await self.dispatch(message)

    async def start(self):
        if self.running:
            return
        self.running = True
        self.task = asyncio.create_task(self.process_queue())

    async def stop(self):
        self.running = False
        if self._task:
            await self._queue.put(None)
            await self._task
            self._task = None
