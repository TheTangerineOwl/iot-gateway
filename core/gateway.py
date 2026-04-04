"""Основной модуль шлюза."""
import asyncio
import logging
import signal
from typing import Any
from typenv import Env
from core.registry import DeviceRegistry
from core.message_bus import MessageBus
from core.pipeline.pipeline import Pipeline
from core.pipeline.stages import (
    ValidationStage, AuthorizationStage
)
from models.device import DeviceStatus, Device
from models.message import Message, MessageType
from storage.sqlite import SQLiteStorage
from storage.subscriber import StorageSubscriber
from protocols.adapter import ProtocolAdapter


env = Env(upper=True)
logger = logging.getLogger(__name__)


class Gateway:
    """Основной модуль работы шлюза."""

    def __init__(self) -> None:
        """Основной модуль работы шлюза."""
        self._adapters: dict[str, ProtocolAdapter] = {}
        self._running = False

        self._bus = MessageBus(
            max_queue=env.int('MESQ_MAX_LEN', default=10000)
        )

        self._registry = DeviceRegistry(
            max_devices=env.int('DEVICES_MAX', default=1000),
            stale_timeout=env.float('DEVICES_TIMEOUT_STALE', default=30.0 * 4)
        )
        self._pipeline = self._build_pipeline()
        self._storage = SQLiteStorage(
            db_path=env.str('STORAGE_DB_PATH', default='data/telemetry.db')
        )
        self._storage_subscriber = StorageSubscriber(self._storage)

    @property
    def is_running(self) -> bool:
        """Работает ли шлюз."""
        return self._running

    def _build_pipeline(self) -> Pipeline:
        """Построить конвейер обработки сообщений."""
        pipeline = Pipeline()

        # тут будет добавление этапов конвейера
        pipeline.add_stage(ValidationStage())
        pipeline.add_stage(AuthorizationStage(self._registry))

        return pipeline

    async def _handle_telemetry(self, message: Message) -> None:
        """Обработать сообщения телеметрии."""
        result = await self._pipeline.execute(message)
        if result:
            await self._registry.heartbeat(result.device_id)
            result.processed = True
            await self._bus.publish(
                f'processed.telemetry.{result.device_id}',
                result
            )

    async def _handle_device_message(self, message: Message) -> None:
        """Обработать технические сообщения."""
        if message.message_type == MessageType.REGISTRATION:
            device = Device.from_dict(message.payload)
            device.protocol = message.protocol
            await self._registry.register(device)

        elif message.message_type == MessageType.HEARTBEAT:
            await self._registry.heartbeat(message.device_id)

        elif message.message_type == MessageType.STATUS:
            status = DeviceStatus(message.payload.get("status", "online"))
            await self._registry.update_status(message.device_id, status)

    def register_adapter(self, adapter: ProtocolAdapter) -> None:
        """Зарегистрировать адаптер протокола."""
        name = adapter.protocol_name
        if name in self._adapters:
            raise ValueError(f"Adapter '{name}' already registered")

        adapter.set_gateway_context(
            message_bus=self._bus,
            registry=self._registry,
        )
        self._adapters[name] = adapter
        logger.debug("Protocol adapter registered: %s", name)

    async def _start(self) -> None:
        """Запуск шлюза."""
        logger.info('Starting gateway')
        await self._storage.setup()
        await self._bus.start()

        self._bus.subscribe("device.*", self._handle_device_message)
        self._bus.subscribe("telemetry.*", self._handle_telemetry)
        self._bus.subscribe(
            "processed.telemetry.*",
            self._storage_subscriber.handle
        )

        await self._pipeline.setup()

        await self._registry.start_monitor(
            check_interval=env.float('DEVICES_CHECK_INTERVAL', default=30.0)
        )

        for name, adapter in self._adapters.items():
            try:
                await adapter.start()
                logger.debug("Adapter '%s' started", name)
            except Exception as exc:
                logger.error(
                    "Failed to start adapter '%s': %s",
                    name,
                    exc,
                    exc_info=True
                )

        self._running = True
        logger.info(
            "Gateway started. Adapters: %s",
            list(self._adapters.keys())
        )

    async def _stop(self) -> None:
        """Остановка шлюза."""
        logger.info("Stoping gateway")
        self._running = False

        for name, adapter in reversed(list(self._adapters.items())):
            try:
                await adapter.stop()
                logger.debug("Adapter '%s' stopped", name)
            except Exception as exc:
                logger.error(
                    "Error stopping adapter '%s': %s",
                    name, exc, exc_info=True
                )

        await self._registry.stop_monitor()
        await self._pipeline.teardown()
        await self._bus.stop()
        await self._storage.teardown()

        logger.info("Gateway stopped")

    async def run_forever(self) -> None:
        """Основной цикл работы шлюза с остановкой по сигналу."""
        await self._start()

        stop_event = asyncio.Event()

        def signal_handler():
            logger.info("Received shutdown signal")
            stop_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, signal_handler)
            except NotImplementedError:
                pass

        try:
            await stop_event.wait()
        except KeyboardInterrupt:
            pass
        finally:
            await self._stop()

    @property
    def status(self) -> dict[str, Any]:
        """Статус работы шлюза."""
        return {
            "gateway": {
                "id": env.int('GATEWAY_ID', default=1),
                "name": env.str('GATEWAY_NAME', default='IoT Gateway'),
                "running": self._running,
            },
            "devices": {
                "total": self._registry.count,
                "online": self._registry.online_count,
            },
            "message_bus": self._bus.stats,
            "pipeline": self._pipeline.stats,
            "adapters": {
                name: {"running": adapter.is_running}
                for name, adapter in self._adapters.items()
            },
        }
