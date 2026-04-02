import asyncio
import logging
from models.device import Device, DeviceStatus


logger = logging.getLogger(__name__)


class DeviceRegistry:
    def __init__(
            self, max_devices: int = 1000, stale_timeout: float = 120.0
    ) -> None:
        self.devices: dict[str, Device] = {}
        self.max_devices = max_devices
        self.stale_timeout = stale_timeout
        self.lock = asyncio.Lock()
        self.task: asyncio.Task | None = None

        self.on_register_callbacks: list = []
        self.on_unregister_callbacks: list = []
        self.on_status_change_callbacks: list = []

    async def register(self, device: Device):
        async with self.lock:
            if (
                device.device_id not in self.devices
                and len(self.devices) >= self.max_devices
            ):
                raise RuntimeError(
                    f"Device limit reached ({self.max_devices}). "
                    f"Cannot register {device.device_id}"
                )

            is_new = device.device_id not in self.devices
            device.touch()
            self.devices[device.device_id] = device

            if is_new:
                logger.info(
                    "Device registered: %s "
                    "(%s, protocol %s)",
                    device.device_id,
                    device.name, device.protocol
                )
                for cb in self.on_register_callbacks:
                    await cb(device)
            else:
                logger.info("Device updated: %s", device.device_id)
        return device

    async def unregister(self, device_id: str):
        async with self.lock:
            device = self.devices.pop(device_id, None)
            if device:
                logger.info("Device unregistered: %s", device_id)
                for cb in self.on_unregister_callbacks:
                    await cb(device)
        return device

    async def update_status(self, device_id: str, status: DeviceStatus):
        device = self.devices.get(device_id)
        if device is None:
            logger.warning(
                "Cannot update status: device %s not found",
                device_id
            )
            return

        old_status = device.device_status
        if old_status != status:
            device.device_status = status
            device.touch()
            logger.info(
                "Device %s status change: "
                "%s -> %s",
                device_id, old_status.value, status.value
            )
            for cb in self.on_status_change_callbacks:
                await cb(device, old_status, status)

    async def heartbeat(self, device_id: str):
        device = self.devices.get(device_id)
        if device:
            device.touch()
            if device.device_status == DeviceStatus.OFFLINE:
                await self.update_status(device_id, DeviceStatus.ONLINE)

    def on_register(self, callback) -> None:
        self.on_register_callbacks.append(callback)

    def on_unregister(self, callback) -> None:
        self.on_unregister_callbacks.append(callback)

    def on_status_change(self, callback) -> None:
        self.on_status_change_callbacks.append(callback)

    async def start_monitor(self, check_interval: float = 30.0) -> None:
        self._monitor_task = asyncio.create_task(
            self.monitor_loop(check_interval)
        )

    async def stop_monitor(self) -> None:
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    async def monitor_loop(self, interval: float) -> None:
        while True:
            await asyncio.sleep(interval)
            await self.check_stale_devices()

    async def check_stale_devices(self) -> None:
        for device in list(self.devices.values()):
            if (
                device.device_status == DeviceStatus.ONLINE
                and device.is_stale(self.stale_timeout)
            ):
                await self.update_status(
                    device.device_id, DeviceStatus.OFFLINE
                )

    @property
    def count(self) -> int:
        return len(self.devices)

    @property
    def online_count(self) -> int:
        return sum(
            1 for d in self.devices.values()
            if d.device_status == DeviceStatus.ONLINE
        )
