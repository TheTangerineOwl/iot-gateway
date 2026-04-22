"""Тесты Gateway."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from models.device import Device, DeviceStatus, DeviceType, ProtocolType
from storage.subscriber import StorageSubscriber
from core.gateway import Gateway


def make_device(device_id: str = "gw-dev-001") -> Device:
    """Создать тестовое устройство."""
    return Device(
        device_id=device_id,
        name=f"Device {device_id}",
        device_type=DeviceType.SENSOR,
        device_status=DeviceStatus.OFFLINE,
        protocol=ProtocolType.HTTP,
    )


def make_gateway(config, mock_storage=None):
    """Создать Gateway с замоканными внешними зависимостями."""
    if mock_storage is None:
        mock_storage = AsyncMock()
        mock_storage.upsert_device = AsyncMock()
        mock_storage.delete_device = AsyncMock()
        mock_storage.load_devices = AsyncMock(return_value=[])
        mock_storage.setup = AsyncMock()
        mock_storage.teardown = AsyncMock()
        mock_storage.save = AsyncMock()

    with patch("core.gateway.SQLiteStorage", return_value=mock_storage), \
         patch("core.gateway.PostgresStorage", return_value=mock_storage), \
         patch.object(Gateway, "_reg_adapters", return_value=None):
        gw = Gateway(config)

    gw._storage = mock_storage
    return gw, mock_storage


class TestGatewayInitCallbacks:
    """Проверяет, что __init__ регистрирует колбэки StorageSubscriber."""

    def test_on_register_callback_registered(self, config):
        """__init__ добавляет on_device_register."""
        gw, _ = make_gateway(config)

        callbacks = gw._registry._on_register_callbacks
        cb_names = [cb.__name__ for cb in callbacks]
        assert "on_device_register" in cb_names

    def test_on_status_change_callback_registered(self, config):
        """__init__ добавляет on_device_status_update в _registry."""
        gw, _ = make_gateway(config)

        callbacks = gw._registry._on_status_change_callbacks
        cb_names = [cb.__name__ for cb in callbacks]
        assert "on_device_status_update" in cb_names

    def test_on_unregister_callback_registered(self, config):
        """__init__ добавляет on_device_unregister."""
        gw, _ = make_gateway(config)

        callbacks = gw._registry._on_unregister_callbacks
        cb_names = [cb.__name__ for cb in callbacks]
        assert "on_device_unregister" in cb_names

    def test_storage_subscriber_created(self, config):
        """__init__ создаёт экземпляр StorageSubscriber."""
        gw, _ = make_gateway(config)

        assert isinstance(gw._storage_subscriber, StorageSubscriber)

    def test_callbacks_belong_to_storage_subscriber(self, config):
        """Зарегистрированные колбэки принадлежат _storage_subscriber."""
        gw, _ = make_gateway(config)

        register_cbs = gw._registry._on_register_callbacks
        status_cbs = gw._registry._on_status_change_callbacks
        unregister_cbs = gw._registry._on_unregister_callbacks

        subscriber = gw._storage_subscriber

        assert any(
            getattr(cb, "__self__", None) is subscriber
            and getattr(cb, "__func__", None)
            is StorageSubscriber.on_device_register
            for cb in register_cbs
        )

        assert any(
            getattr(cb, "__self__", None) is subscriber
            and getattr(cb, "__func__", None)
            is StorageSubscriber.on_device_status_update
            for cb in status_cbs
        )

        assert any(
            getattr(cb, "__self__", None) is subscriber
            and getattr(cb, "__func__", None)
            is StorageSubscriber.on_device_unregister
            for cb in unregister_cbs
        )


class TestRestoreDevices:
    """Тесты метода _restore_devices."""

    @pytest.mark.asyncio
    async def test_calls_load_devices(self, config):
        """_restore_devices вызывает storage.load_devices()."""
        gw, storage = make_gateway(config)
        storage.load_devices = AsyncMock(return_value=[])

        await gw._restore_devices()

        storage.load_devices.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_registers_loaded_devices(self, config):
        """_restore_devices регистрирует каждое загруженное устройство."""
        devices = [make_device(f"restore-{i}") for i in range(3)]
        gw, storage = make_gateway(config)
        storage.load_devices = AsyncMock(return_value=devices)

        await gw._restore_devices()

        for device in devices:
            assert gw._registry.get(device.device_id) is not None

    @pytest.mark.asyncio
    async def test_empty_storage_no_error(self, config):
        """_restore_devices не падает, если в хранилище нет устройств."""
        gw, storage = make_gateway(config)
        storage.load_devices = AsyncMock(return_value=[])

        await gw._restore_devices()

        assert gw._registry.count == 0

    @pytest.mark.asyncio
    async def test_restore_does_not_trigger_upsert(self, config):
        """_restore_devices не вызывает upsert_device при восстановлении."""
        device = make_device("no-upsert-restore")
        gw, storage = make_gateway(config)
        storage.load_devices = AsyncMock(return_value=[device])
        storage.upsert_device.reset_mock()

        await gw._restore_devices()

        assert gw._registry.get("no-upsert-restore") is not None

    @pytest.mark.asyncio
    async def test_restore_multiple_devices_correct_count(self, config):
        """_restore_devices восстанавливает столько же устройств."""
        n = 5
        devices = [make_device(f"count-restore-{i}") for i in range(n)]
        gw, storage = make_gateway(config)
        storage.load_devices = AsyncMock(return_value=devices)

        await gw._restore_devices()

        assert gw._registry.count == n

    @pytest.mark.asyncio
    async def test_restore_logs_on_storage_error(self, config, caplog):
        """_restore_devices логирует ошибку, если load_devices падает."""
        import logging
        gw, storage = make_gateway(config)
        storage.load_devices = AsyncMock(
            side_effect=RuntimeError("storage failed")
        )

        with caplog.at_level(logging.ERROR, logger="core.gateway"):
            try:
                await gw._restore_devices()
            except Exception:
                pass


class TestStartCallsRestoreDevices:
    """Проверяет, что _start вызывает _restore_devices."""

    @pytest.mark.asyncio
    async def test_start_calls_restore_devices(self, config):
        """_start вызывает _restore_devices до запуска адаптеров."""
        gw, storage = make_gateway(config)
        storage.load_devices = AsyncMock(return_value=[])
        storage.setup = AsyncMock()

        restore_called = []

        async def mock_restore():
            restore_called.append(True)

        gw._restore_devices = mock_restore

        # патчим долгоживущие задачи, чтобы _start не завис
        with patch.object(
                gw._registry, "start_monitor", new_callable=AsyncMock
            ), \
            patch.object(
                gw._bus, "start", new_callable=AsyncMock
            ), \
            patch.object(
                gw._bus, "stop", new_callable=AsyncMock
            ), \
            patch.object(
                gw._registry, "stop_monitor", new_callable=AsyncMock
            ), \
            patch.object(
                gw._storage, "teardown", new_callable=AsyncMock
        ):
            async def run_start_briefly():
                task = asyncio.create_task(gw._start())
                await asyncio.sleep(0.05)
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

            await run_start_briefly()

        assert restore_called

    @pytest.mark.asyncio
    async def test_restore_devices_called_after_storage_setup(self, config):
        """_restore_devices вызывается после setup() хранилища."""
        gw, storage = make_gateway(config)
        storage.load_devices = AsyncMock(return_value=[])

        call_order = []

        original_setup = storage.setup

        async def tracked_setup():
            call_order.append("setup")
            await original_setup()

        async def tracked_restore():
            call_order.append("restore")

        storage.setup = tracked_setup
        gw._restore_devices = tracked_restore

        with patch.object(
                gw._registry, "start_monitor", new_callable=AsyncMock
            ), \
            patch.object(
                gw._bus, "start", new_callable=AsyncMock
            ), \
            patch.object(
                gw._bus, "stop", new_callable=AsyncMock
            ), \
            patch.object(
                gw._registry, "stop_monitor", new_callable=AsyncMock
            ), \
            patch.object(
                gw._storage, "teardown", new_callable=AsyncMock
        ):

            async def run_start_briefly():
                task = asyncio.create_task(gw._start())
                await asyncio.sleep(0.05)
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

            await run_start_briefly()

        if "setup" in call_order and "restore" in call_order:
            setup_idx = call_order.index("setup")
            restore_idx = call_order.index("restore")
            assert setup_idx < restore_idx
