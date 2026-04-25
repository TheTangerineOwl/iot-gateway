"""
Трекер команд с поддержкой ожидания ответа (request-response поверх шины).

Позволяет:
    result = await tracker.send_and_wait(message, timeout=10.0)
"""
import asyncio
import logging
from models.message import Message


logger = logging.getLogger(__name__)


class CommandTracker:
    """Реестр ожидающих ответа команд."""

    def __init__(self) -> None:
        """Реестр ожидающих ответа команд."""
        self._pending: dict[str, asyncio.Future[Message]] = {}

    def register(self, message_id: str) -> asyncio.Future[Message]:
        """Зарегистрировать ожидание ответа на команду."""
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[Message] = loop.create_future()
        self._pending[message_id] = fut
        return fut

    def resolve(self, message: Message) -> bool:
        """
        Зарезолвить Future, если есть ожидающий запрос.

        Возвращает True, если кто-то ждал ответ.
        """
        fut = self._pending.pop(message.message_id, None)
        if fut and not fut.done():
            fut.set_result(message)
            return True
        return False

    async def send_and_wait(
        self,
        message: Message,
        bus_publish_coro,
        timeout: float = 10.0,
    ) -> Message | None:
        """
        Опубликовать команду и дождаться ответа.

        Args:
            message:           сообщение с командой.
            bus_publish_coro:  корутина bus.publish(topic, message).
            timeout:           сколько секунд ждать ответа.

        Returns:
            Message с ответом или None при таймауте.
        """
        fut = self.register(message.message_id)
        await bus_publish_coro
        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(
                "No response for command '%s' in %.1f s",
                message.message_id, timeout,
            )
            self._pending.pop(message.message_id, None)
            return None
