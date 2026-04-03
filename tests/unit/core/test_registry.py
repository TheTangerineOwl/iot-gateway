"""Тесты реестра устройств."""
import asyncio
import pytest
from unittest.mock import AsyncMock
from time import time
from core.registry import DeviceRegistry
from models.device import Device, DeviceStatus, DeviceType, ProtocolType


@pytest.fixture
def registry():
    """Реестр с маленьким лимитом устройств и долгим stale-таймаутом."""
    return DeviceRegistry(max_devices=5, stale_timeout=120.0)


@pytest.fixture
def device():
    """Устройство со всеми явными полями, чтобы тесты не зависели от uuid4."""
    return Device(
        device_id="dev-001",
        name="Thermometer",
        device_type=DeviceType.SENSOR,
        device_status=DeviceStatus.OFFLINE,
        protocol=ProtocolType.HTTP,
    )


@pytest.fixture
def online_device():
    """Устройство, уже находящееся в статусе ONLINE."""
    return Device(
        device_id="dev-online",
        name="Hygrometer",
        device_type=DeviceType.SENSOR,
        device_status=DeviceStatus.ONLINE,
        protocol=ProtocolType.MQTT,
    )


class TestRegister:
    """Тесты для register()."""

    @pytest.mark.asyncio
    async def test_register_count(self, registry, device):
        """После регистрации count == 1."""
        await registry.register(device)
        assert registry.count == 1

    @pytest.mark.asyncio
    async def test_return_on_register(self, registry, device):
        """register() возвращает тот же объект устройства."""
        result = await registry.register(device)
        assert result is device

    @pytest.mark.asyncio
    async def test_register_touch(self, registry, device):
        """После регистрации last_response обновляется (> 0)."""
        before = time()
        await registry.register(device)
        assert device.last_response >= before

    @pytest.mark.asyncio
    async def test_register_double(
        self, registry, device
    ):
        """
        Тест повторной регистрации.

        Повторная регистрация того же device_id — не новый девайс,
        count не растёт.
        """
        await registry.register(device)
        await registry.register(device)
        assert registry.count == 1

    @pytest.mark.asyncio
    async def test_register_callback(self, registry, device):
        """Callback on_register вызывается один раз."""
        cb = AsyncMock()
        registry.on_register(cb)

        await registry.register(device)
        await registry.register(device)

        cb.assert_awaited_once_with(device)

    @pytest.mark.asyncio
    async def test_register_multiple_callbacks(self, registry, device):
        """Все зарегистрированные on_register-колбэки вызываются."""
        cb1, cb2 = AsyncMock(), AsyncMock()
        registry.on_register(cb1)
        registry.on_register(cb2)

        await registry.register(device)

        cb1.assert_awaited_once_with(device)
        cb2.assert_awaited_once_with(device)

    @pytest.mark.asyncio
    async def test_register_max_devices(self, registry):
        """При превышении лимита устройств бросается RuntimeError."""
        for i in range(registry._max_devices):
            await registry.register(Device(device_id=f"dev-{i}"))

        with pytest.raises(RuntimeError, match="Device limit reached"):
            await registry.register(Device(device_id="overflow"))

    @pytest.mark.asyncio
    async def test_register_existing_on_full(
        self, registry, device
    ):
        """Если реестр полон, но device_id уже есть — обновление."""
        await registry.register(device)
        for i in range(registry._max_devices - 1):
            await registry.register(Device(device_id=f"extra-{i}"))

        await registry.register(device)
        assert registry.count == registry._max_devices


class TestUnregister:
    """Тесты для unregister()."""

    @pytest.mark.asyncio
    async def test_unregister_removes(self, registry, device):
        """После unregister count == 0."""
        await registry.register(device)
        await registry.unregister(device.device_id)
        assert registry.count == 0

    @pytest.mark.asyncio
    async def test_unregister_return(self, registry, device):
        """unregister() возвращает удалённый объект устройства."""
        await registry.register(device)
        result = await registry.unregister(device.device_id)
        assert result is device

    @pytest.mark.asyncio
    async def test_unregister_unknown(self, registry):
        """Удаление несуществующего device_id не бросает ошибку."""
        result = await registry.unregister("ghost-device")
        assert result is None

    @pytest.mark.asyncio
    async def test_unregister_callback(self, registry, device):
        """Callback on_unregister вызывается при удалении."""
        cb = AsyncMock()
        registry.on_unregister(cb)

        await registry.register(device)
        await registry.unregister(device.device_id)

        cb.assert_awaited_once_with(device)

    @pytest.mark.asyncio
    async def test_unregister_unknown_callback(self, registry):
        """Callback on_unregister не вызывается, если устройство не найдено."""
        cb = AsyncMock()
        registry.on_unregister(cb)

        await registry.unregister("ghost-device")

        cb.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unregister_slot(self, registry, device):
        """После удаления освобождается слот."""
        for i in range(registry._max_devices):
            await registry.register(Device(device_id=f"dev-{i}"))

        await registry.unregister("dev-0")
        await registry.register(Device(device_id="new-dev"))

        assert registry.count == registry._max_devices


class TestUpdateStatus:
    """Тест update_status()."""

    @pytest.mark.asyncio
    async def test_status_changes(self, registry, device):
        """Статус обновляется, если новое значение отличается."""
        await registry.register(device)
        await registry.update_status(device.device_id, DeviceStatus.ONLINE)
        assert device.device_status == DeviceStatus.ONLINE

    @pytest.mark.asyncio
    async def test_status_callback(self, registry, device):
        """Callback on_status_change вызывается при смене статуса."""
        cb = AsyncMock()
        registry.on_status_change(cb)

        await registry.register(device)
        await registry.update_status(device.device_id, DeviceStatus.ONLINE)

        cb.assert_awaited_once_with(
            device, DeviceStatus.OFFLINE, DeviceStatus.ONLINE
        )

    @pytest.mark.asyncio
    async def test_status_callback_same(self, registry, device):
        """Callback не вызывается, если статус не изменился."""
        cb = AsyncMock()
        registry.on_status_change(cb)

        await registry.register(device)
        await registry.update_status(device.device_id, DeviceStatus.OFFLINE)

        cb.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_status_unknown(self, registry):
        """update_status для несуществующего не бросает исключение."""
        await registry.update_status("ghost", DeviceStatus.ONLINE)

    @pytest.mark.asyncio
    async def test_status_change_calls_touch(self, registry, device):
        """При смене статуса обновляется last_response."""
        await registry.register(device)
        before = time()
        await registry.update_status(device.device_id, DeviceStatus.ERROR)
        assert device.last_response >= before


class TestHeartbeat:
    """Тест heartbeat()."""

    @pytest.mark.asyncio
    async def test_heartbeat_updates_last_response(self, registry, device):
        """heartbeat() обновляет last_response устройства."""
        await registry.register(device)
        old = device.last_response
        await asyncio.sleep(0.01)
        await registry.heartbeat(device.device_id)
        assert device.last_response > old

    @pytest.mark.asyncio
    async def test_heartbeat_brings_online(self, registry, device):
        """heartbeat() переводит OFFLINE в ONLINE."""
        await registry.register(device)
        await registry.heartbeat(device.device_id)
        assert device.device_status == DeviceStatus.ONLINE

    @pytest.mark.asyncio
    async def test_heartbeat_keeps_online(self, registry, online_device):
        """heartbeat() не меняет статус устройства, уже находящегося ONLINE."""
        cb = AsyncMock()
        registry.on_status_change(cb)

        await registry.register(online_device)
        await registry.heartbeat(online_device.device_id)

        cb.assert_not_awaited()
        assert online_device.device_status == DeviceStatus.ONLINE

    @pytest.mark.asyncio
    async def test_heartbeat_unknown(self, registry):
        """heartbeat() для несуществующего device_id не бросает исключение."""
        await registry.heartbeat("ghost-device")


class TestCounters:
    """Тесты для свойств count и online_count."""

    @pytest.mark.asyncio
    async def test_online_count_zero_on_start(self, registry):
        """Начинает с нуля."""
        assert registry.online_count == 0

    @pytest.mark.asyncio
    async def test_online_count_increment(self, registry, device):
        """Увеличивает на 1 при переходе в ONLINE."""
        await registry.register(device)
        await registry.update_status(device.device_id, DeviceStatus.ONLINE)
        assert registry.online_count == 1

    @pytest.mark.asyncio
    async def test_online_count_decrement(self, registry, device):
        """Уменьшает на 1 при переходе из ONLINE."""
        await registry.register(device)
        await registry.update_status(device.device_id, DeviceStatus.ONLINE)
        await registry.update_status(device.device_id, DeviceStatus.OFFLINE)
        assert registry.online_count == 0

    @pytest.mark.asyncio
    async def test_count_reg_unreg(self, registry, device):
        """Изменяется при регистрации-удалении."""
        await registry.register(device)
        assert registry.count == 1
        await registry.unregister(device.device_id)
        assert registry.count == 0


class TestStaleMonitor:
    """Тест монитора просроченных устройств."""

    @pytest.mark.asyncio
    async def test_stale_online_device_offline(self):
        """Устройство с is_stale() == True переводится в OFFLINE монитором."""
        registry = DeviceRegistry(max_devices=5, stale_timeout=0.0)
        device = Device(
            device_id="stale-dev",
            device_status=DeviceStatus.ONLINE,
        )
        await registry.register(device)

        device.last_response = time() - 9999

        await registry._check_stale_devices()

        assert device.device_status == DeviceStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_fresh_online(self, registry, online_device):
        """Свежее устройство не трогается монитором."""
        await registry.register(online_device)
        online_device.touch()

        await registry._check_stale_devices()

        assert online_device.device_status == DeviceStatus.ONLINE

    @pytest.mark.asyncio
    async def test_offline_device_not_touched(self):
        """Уже OFFLINE устройство монитор не трогает."""
        registry = DeviceRegistry(max_devices=5, stale_timeout=0.0)
        cb = AsyncMock()
        registry.on_status_change(cb)

        device = Device(device_id="cold", device_status=DeviceStatus.OFFLINE)
        await registry.register(device)
        device.last_response = time() - 9999

        await registry._check_stale_devices()

        cb.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_start_and_stop_monitor(self, registry):
        """start_monitor / stop_monitor не бросают исключений."""
        await registry.start_monitor(check_interval=60.0)
        await registry.stop_monitor()
