"""Тесты реестра устройства."""
import asyncio
import pytest
from time import time
from unittest.mock import AsyncMock
from core.registry import DeviceRegistry
from models.device import DeviceStatus, Device
from tests.conftest import not_raises


class TestGet:
    """Тест получения девайса из регистра по device_id."""

    @pytest.mark.asyncio
    async def test_get_existing(
        self,
        device: Device,
        registry: DeviceRegistry
    ):
        """Если такой device_id зарегистрирован, вернуть девайс."""
        await registry.register(device)
        assert registry.get(device.device_id) is not None

    @pytest.mark.asyncio
    async def test_get_unknown_returns_none(
        self,
        registry: DeviceRegistry
    ):
        """Если такого device_id нет, вернуть None."""
        with not_raises(Exception):
            assert registry.get('unknown') is None


class TestRegister:
    """Тесты для регистрации устройства."""

    @pytest.mark.asyncio
    async def test_register_count(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """После регистрации count == 1."""
        await registry.register(device)
        assert registry.count == 1

    @pytest.mark.asyncio
    async def test_return_on_register(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """register() возвращает тот же объект устройства."""
        result = await registry.register(device)
        assert result is device

    @pytest.mark.asyncio
    async def test_register_touch(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """После регистрации last_response обновляется (> 0)."""
        before = time()
        await asyncio.sleep(0)
        await registry.register(device)
        assert device.last_response >= before

    @pytest.mark.asyncio
    async def test_register_double(
        self,
        registry: DeviceRegistry,
        device: Device
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
    async def test_register_callback(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """Callback on_register вызывается один раз."""
        cb = AsyncMock()
        registry.on_register(cb)

        await registry.register(device)
        await registry.register(device)

        cb.assert_awaited_once_with(device)

    @pytest.mark.asyncio
    async def test_register_multiple_callbacks(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """Все зарегистрированные on_register-колбэки вызываются."""
        cb1, cb2 = AsyncMock(), AsyncMock()
        registry.on_register(cb1)
        registry.on_register(cb2)

        await registry.register(device)

        cb1.assert_awaited_once_with(device)
        cb2.assert_awaited_once_with(device)

    @pytest.mark.asyncio
    async def test_register_max_devices(
        self,
        registry: DeviceRegistry
    ):
        """При превышении лимита устройств бросается RuntimeError."""
        for i in range(registry._max_devices):
            await registry.register(Device(device_id=f"dev-{i}"))

        with pytest.raises(RuntimeError, match="Device limit reached"):
            await registry.register(Device(device_id="overflow"))

    @pytest.mark.asyncio
    async def test_register_existing_on_full(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """Если реестр полон, но device_id уже есть — обновление."""
        await registry.register(device)
        for i in range(registry._max_devices - 1):
            await registry.register(Device(device_id=f"extra-{i}"))
        with not_raises(Exception):
            await registry.register(device)
        assert registry.count == registry._max_devices


class TestUnregister:
    """Тесты для удаления устройства."""

    @pytest.mark.asyncio
    async def test_unregister_removes(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """После unregister count == 0."""
        await registry.register(device)
        await registry.unregister(device.device_id)
        assert registry.count == 0

    @pytest.mark.asyncio
    async def test_unregister_return(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """unregister() возвращает удалённый объект устройства."""
        await registry.register(device)
        result = await registry.unregister(device.device_id)
        assert result is device

    @pytest.mark.asyncio
    async def test_unregister_unknown(
        self,
        registry: DeviceRegistry
    ):
        """Удаление несуществующего device_id не бросает ошибку."""
        with not_raises(Exception):
            result = await registry.unregister("ghost-device")
        assert result is None

    @pytest.mark.asyncio
    async def test_unregister_callback(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """Callback on_unregister вызывается при удалении."""
        cb = AsyncMock()
        registry.on_unregister(cb)

        await registry.register(device)
        await registry.unregister(device.device_id)

        cb.assert_awaited_once_with(device)

    @pytest.mark.asyncio
    async def test_unregister_unknown_callback(
        self,
        registry: DeviceRegistry
    ):
        """Callback on_unregister не вызывается, если устройство не найдено."""
        cb = AsyncMock()
        registry.on_unregister(cb)

        with not_raises(Exception):
            await registry.unregister("ghost-device")

        cb.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unregister_multiple_callbacks(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """Все зарегистрированные on_unregister-колбэки вызываются."""
        cb1, cb2 = AsyncMock(), AsyncMock()
        registry.on_unregister(cb1)
        registry.on_unregister(cb2)

        await registry.register(device)
        await registry.unregister(device.device_id)

        cb1.assert_awaited_once_with(device)
        cb2.assert_awaited_once_with(device)

    @pytest.mark.asyncio
    async def test_unregister_slot(
        self,
        registry: DeviceRegistry
    ):
        """После удаления освобождается слот."""
        for i in range(registry._max_devices):
            await registry.register(Device(device_id=f"dev-{i}"))

        await registry.unregister("dev-0")
        with not_raises(Exception):
            await registry.register(Device(device_id="new-dev"))

        assert registry.count == registry._max_devices


class TestUpdateStatus:
    """Тесты обновления статуса."""

    @pytest.mark.asyncio
    async def test_status_changes(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """Статус обновляется, если новое значение отличается."""
        await registry.register(device)
        await registry.update_status(device.device_id, DeviceStatus.ONLINE)
        assert device.device_status == DeviceStatus.ONLINE

    @pytest.mark.asyncio
    async def test_status_callback(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """Callback on_status_change вызывается при смене статуса."""
        cb = AsyncMock()
        registry.on_status_change(cb)

        await registry.register(device)
        await registry.update_status(device.device_id, DeviceStatus.OFFLINE)

        cb.assert_awaited_once_with(
            device, DeviceStatus.ONLINE, DeviceStatus.OFFLINE
        )

    @pytest.mark.asyncio
    async def test_status_callback_same(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """Callback не вызывается, если статус не изменился."""
        cb = AsyncMock()
        registry.on_status_change(cb)

        await registry.register(device)
        await registry.update_status(device.device_id, DeviceStatus.ONLINE)

        cb.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_status_unknown(
        self,
        registry: DeviceRegistry
    ):
        """update_status для несуществующего не бросает исключение."""
        with not_raises(Exception):
            await registry.update_status("NOT_EXISTS", DeviceStatus.ONLINE)

    @pytest.mark.asyncio
    async def test_status_change_calls_touch(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """При смене статуса обновляется last_response."""
        await registry.register(device)
        before = time()
        await asyncio.sleep(0)
        await registry.update_status(device.device_id, DeviceStatus.ERROR)
        assert device.last_response >= before


class TestHeartbeat:
    """Тесты сердцебиения."""

    @pytest.mark.asyncio
    async def test_heartbeat_updates_last_response(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """heartbeat() обновляет last_response устройства."""
        await registry.register(device)
        old = device.last_response
        await asyncio.sleep(0)
        await registry.heartbeat(device.device_id)
        assert device.last_response > old

    @pytest.mark.asyncio
    async def test_heartbeat_brings_online(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """heartbeat() переводит OFFLINE в ONLINE."""
        await registry.register(device)
        await registry.heartbeat(device.device_id)
        assert device.device_status == DeviceStatus.ONLINE

    @pytest.mark.asyncio
    async def test_heartbeat_keeps_online(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """heartbeat() не меняет статус устройства, уже находящегося ONLINE."""
        cb = AsyncMock()
        registry.on_status_change(cb)

        await registry.register(device)
        await registry.heartbeat(device.device_id)

        cb.assert_not_awaited()
        assert device.device_status == DeviceStatus.ONLINE

    @pytest.mark.asyncio
    async def test_heartbeat_unknown(
        self,
        registry: DeviceRegistry
    ):
        """heartbeat() для несуществующего device_id не бросает исключение."""
        with not_raises(Exception):
            await registry.heartbeat("ghost-device")


class TestProperties:
    """Тесты свойств регистра."""

    @pytest.mark.asyncio
    async def test_count_empty(
        self,
        registry: DeviceRegistry
    ):
        """У пустого регистра count = 0."""
        assert registry.count == 0

    @pytest.mark.asyncio
    async def test_online_count(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """Если в регистре 1 онлайн-устройство, то online_count = 1."""
        await registry.register(device)
        offline = Device(device_id='dev-off')
        await registry.register(offline)
        await registry.update_status(
            offline.device_id,
            DeviceStatus.SLEEPING
        )
        assert registry.count == 2
        assert registry.online_count == 1


class TestMonitor:
    """Тесты фонового монитора stale-устройств."""

    @pytest.mark.asyncio
    async def test_stale_device_goes_offline(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """ONLINE-устройство с истёкшим last_response переходит в OFFLINE."""
        device.device_status = DeviceStatus.ONLINE

        await registry.register(device)
        device.last_response = time() - 999
        await registry._check_stale_devices()

        assert device.device_status == DeviceStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_offline_device_not_touched(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """OFFLINE-устройство не меняет статус даже при stale."""
        device.device_status = DeviceStatus.OFFLINE

        await registry.register(device)
        device.last_response = time() - 999
        cb = AsyncMock()
        registry.on_status_change(cb)
        await registry._check_stale_devices()

        cb.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_fresh_online_not_marked_stale(
        self,
        registry: DeviceRegistry,
        device: Device
    ):
        """Свежее ONLINE-устройство не уходит в OFFLINE."""
        device.device_status = DeviceStatus.ONLINE
        await registry.register(device)

        await registry._check_stale_devices()

        assert device.device_status == DeviceStatus.ONLINE
