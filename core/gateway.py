import asyncio
import logging
import signal
from typing import Any

from core.registry import DeviceRegistry
from core.message_bus import MessageBus
from core.pipeline.pipeline import Pipeline
from core.pipeline.stages import (ValidationStage)
from models.device import DeviceStatus, Device
from models.message import Message, MessageType
from protocols.adapter import ProtocolAdapter


logger = logging.getLogger(__name__)


class Gateway:
    def __init__(self) -> None:
        self.adapters: dict[str, ProtocolAdapter] = {}
        self.running = False

        self.bus = MessageBus()
        self.registry = DeviceRegistry(
            max_devices=1000,
            stale_timeout=30 * 4,
        )
        self.pipeline = self.build_pipeline()

    @property
    def is_running(self) -> bool:
        return self.running

    def build_pipeline(self) -> Pipeline:
        pipeline = Pipeline()

        # тут будет добавление этапов конвейера
        pipeline.add_stage(ValidationStage())

        return pipeline

    async def handle_telemetry(self, message: Message) -> None:
        result = await self.pipeline.execute(message)
        if result:
            await self.registry.heartbeat(result.device_id)
            # Дальше — в хранилище / облако ( когда будет)
            # await self.bus.publish("processed.telemetry", result)

    async def handle_device_message(self, message: Message) -> None:
        if message.message_type == MessageType.REGISTRATION:
            device = Device.from_dict(message.payload)
            device.protocol = message.protocol
            await self.registry.register(device)

        elif message.message_type == MessageType.HEARTBEAT:
            await self.registry.heartbeat(message.device_id)

        elif message.message_type == MessageType.STATUS:
            status = DeviceStatus(message.payload.get("status", "online"))
            await self.registry.update_status(message.device_id, status)

    def register_adapter(self, adapter: ProtocolAdapter) -> None:
        name = adapter.protocol_name
        if name in self.adapters:
            raise ValueError(f"Adapter '{name}' already registered")

        adapter.set_gateway_context(
            message_bus=self.bus,
            registry=self.registry,
        )
        self.adapters[name] = adapter
        logger.debug("Protocol adapter registered: %s", name)

    async def start(self) -> None:
        logger.info('Starting gateway')

        await self.bus.start()

        self.bus.subscribe("device.*", self.handle_device_message)
        self.bus.subscribe("telemetry.*", self.handle_telemetry)

        await self.pipeline.setup()

        await self.registry.start_monitor(check_interval=30)

        for name, adapter in self.adapters.items():
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

        self.running = True
        logger.info(
            "Gateway started. Adapters: %s",
            list(self.adapters.keys())
        )

    async def stop(self) -> None:
        logger.info("Stoping gateway")
        self._running = False

        for name, adapter in reversed(list(self.adapters.items())):
            try:
                await adapter.stop()
                logger.debug("Adapter '%s' stopped", name)
            except Exception as exc:
                logger.error(
                    "Error stopping adapter '%s': %s",
                    name, exc, exc_info=True
                )

        await self.registry.stop_monitor()
        await self.pipeline.teardown()
        await self.bus.stop()

        logger.info("Gateway stopped")

    async def run_forever(self) -> None:
        await self.start()

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
            await self.stop()

    def status(self) -> dict[str, Any]:
        return {
            "gateway": {
                # "id":
                # "name":
                "running": self._running,
            },
            "devices": {
                "total": self.registry.count,
                "online": self.registry.online_count,
            },
            "message_bus": self.bus.stats,
            "pipeline": self.pipeline.stats,
            "adapters": {
                name: {"running": adapter.is_running}
                for name, adapter in self.adapters.items()
            },
        }
