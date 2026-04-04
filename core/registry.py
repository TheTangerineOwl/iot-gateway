"""Регистр девайсов."""
import asyncio
import logging
from models.device import Device, DeviceStatus


logger = logging.getLogger(__name__)


class DeviceRegistry:
    """Регистр девайсов."""

    def __init__(
            self, max_devices: int = 1000, stale_timeout: float = 120.0
    ) -> None:
        """Регистр девайсов с функциями регистрации и обновления состояния."""
        self._devices: dict[str, Device] = {}
        self._max_devices = max_devices
        self._stale_timeout = stale_timeout
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None

        self._on_register_callbacks: list = []
        self._on_unregister_callbacks: list = []
        self._on_status_change_callbacks: list = []

    def get(self, device_id: str) -> Device | None:
        """Получить зарегистрированный девайс."""
        return self._devices.get(device_id, None)

    async def register(self, device: Device):
        """Зарегистрировать девайс."""
        async with self._lock:
            if (
                device.device_id not in self._devices
                and len(self._devices) >= self._max_devices
            ):
                raise RuntimeError(
                    f"Device limit reached ({self._max_devices}). "
                    f"Cannot register {device.device_id}"
                )

            is_new = device.device_id not in self._devices
            device.touch()
            self._devices[device.device_id] = device

            if is_new:
                logger.info(
                    "Device registered: %s "
                    "(%s, protocol %s)",
                    device.device_id,
                    device.name, device.protocol
                )
                for cb in self._on_register_callbacks:
                    await cb(device)
            else:
                logger.info("Device updated: %s", device.device_id)
        return device

    async def unregister(self, device_id: str):
        """Удалить девайс."""
        async with self._lock:
            device = self._devices.pop(device_id, None)
            if device:
                logger.info("Device unregistered: %s", device_id)
                for cb in self._on_unregister_callbacks:
                    await cb(device)
        return device

    async def update_status(self, device_id: str, status: DeviceStatus):
        """Обновить статус девайса."""
        device = self._devices.get(device_id)
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
            for cb in self._on_status_change_callbacks:
                await cb(device, old_status, status)

    async def heartbeat(self, device_id: str):
        """Проверка связи с девайсом."""
        device = self._devices.get(device_id)
        if device:
            device.touch()
            if device.device_status == DeviceStatus.OFFLINE:
                await self.update_status(device_id, DeviceStatus.ONLINE)

    def on_register(self, callback) -> None:
        """Добавление обработчика события регистрации."""
        self._on_register_callbacks.append(callback)

    def on_unregister(self, callback) -> None:
        """Добавление обработчика события удаления."""
        self._on_unregister_callbacks.append(callback)

    def on_status_change(self, callback) -> None:
        """Добавление обработчика изменения состояния."""
        self._on_status_change_callbacks.append(callback)

    async def start_monitor(self, check_interval: float = 30.0) -> None:
        """Запустить монитор состояний девайсов."""
        self._monitor_task = asyncio.create_task(
            self._monitor_loop(check_interval)
        )

    async def stop_monitor(self) -> None:
        """Остановить монитор состояний девайсов."""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self, interval: float) -> None:
        """Цикл монитора состояний."""
        while True:
            await asyncio.sleep(interval)
            await self._check_stale_devices()

    async def _check_stale_devices(self) -> None:
        """Проверяет, не просрочено ли подключение к девайсу."""
        for device in list(self._devices.values()):
            if (
                device.device_status == DeviceStatus.ONLINE
                and device.is_stale(self._stale_timeout)
            ):
                await self.update_status(
                    device.device_id, DeviceStatus.OFFLINE
                )

    @property
    def count(self) -> int:
        """Количество зарегистрированных девайсов."""
        return len(self._devices)

    @property
    def online_count(self) -> int:
        """Количество девайсов в сети."""
        return sum(
            1 for d in self._devices.values()
            if d.device_status == DeviceStatus.ONLINE
        )
