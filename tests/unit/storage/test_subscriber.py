"""Тест подписчика хранилища."""
import pytest
from unittest.mock import AsyncMock
from models.device import Device, DeviceStatus, DeviceType, ProtocolType
from models.message import Message, MessageType
from models.telemetry import TelemetryRecord
from storage.subscriber import StorageSubscriber


@pytest.fixture
def subscriber(mock_storage):
    """Подписчик с мок-хранилищем."""
    return StorageSubscriber(mock_storage)


class TestStorageSubscriber:
    """Тест подписчика хранилища."""

    class TestHandle:
        """Тест обработчика."""

        @pytest.mark.asyncio
        async def test_handle_saves_record(
            self,
            mock_storage: AsyncMock,
            telemetry_message: Message
        ):
            """Обработчик вызывает storage.save с корректной записью."""
            telemetry_message.processed = True
            subscriber = StorageSubscriber(mock_storage)
            telemetry_message.processed = True

            await subscriber.handle(telemetry_message)

            mock_storage.save.assert_awaited_once()
            saved_record = mock_storage.save.call_args[0][0]
            assert saved_record == TelemetryRecord.from_message(
                telemetry_message
            )

        @pytest.mark.asyncio
        async def test_handle_storage_error(
            self,
            mock_storage: AsyncMock,
            telemetry_message: Message
        ):
            """Шина должна оставаться живой."""
            telemetry_message.processed = True
            mock_storage.save.side_effect = Exception("Test storage error")
            subscriber = StorageSubscriber(mock_storage)

            await subscriber.handle(telemetry_message)

        @pytest.mark.asyncio
        async def test_handle_record_all_fields(
            self,
            mock_storage: AsyncMock,
            telemetry_message: Message
        ):
            """Запись создается со всеми полями сообщения."""
            telemetry_message.processed = True
            subscriber = StorageSubscriber(mock_storage)
            await subscriber.handle(telemetry_message)

            mock_storage.save.assert_awaited_once()
            record = mock_storage.save.call_args[0][0]

            expected = TelemetryRecord.from_message(telemetry_message)
            assert record == expected

        @pytest.mark.asyncio
        async def test_handle_storage_error_does_not_raise(
            self,
            mock_storage: AsyncMock,
            telemetry_message: Message
        ):
            """Ошибка не пробрасывается наружу, шина продолжает работу."""
            telemetry_message.processed = True
            mock_storage.save.side_effect = Exception("disk full")
            subscriber = StorageSubscriber(mock_storage)

            # не должно поднимать исключение
            await subscriber.handle(telemetry_message)

        @pytest.mark.asyncio
        async def test_handle_storage_error_save_was_attempted(
            self,
            mock_storage: AsyncMock,
            telemetry_message: Message
        ):
            """Даже при ошибке вызов был совершён и не проигнорирован."""
            telemetry_message.processed = True
            mock_storage.save.side_effect = Exception("timeout")
            subscriber = StorageSubscriber(mock_storage)

            await subscriber.handle(telemetry_message)

            mock_storage.save.assert_awaited_once()

        @pytest.mark.asyncio
        async def test_handle_non_telemetry_message_still_saves(
            self,
            mock_storage: AsyncMock,
            telemetry_message: Message
        ):
            """Сохраняет любое сообщение."""
            telemetry_message.processed = True
            telemetry_message.message_type == MessageType.REGISTRATION
            subscriber = StorageSubscriber(mock_storage)

            await subscriber.handle(telemetry_message)

            mock_storage.save.assert_awaited_once()

    class TestOnDeviceRegister:
        """Тесты колбэка on_device_register."""

        @pytest.mark.asyncio
        async def test_calls_upsert_device(
            self,
            subscriber,
            mock_storage,
            device
        ):
            """on_device_register вызывает storage.upsert_device."""
            await subscriber.on_device_register(device)

            mock_storage.upsert_device.assert_awaited_once_with(device)

        @pytest.mark.asyncio
        async def test_does_not_raise_on_storage_error(
            self, subscriber, mock_storage, device
        ):
            """on_device_register не пробрасывает исключение при ошибке."""
            mock_storage.upsert_device.side_effect = RuntimeError(
                "DB unavailable"
            )

            # не должно бросить исключение наружу
            await subscriber.on_device_register(device)

        @pytest.mark.asyncio
        async def test_delete_not_called_on_register(
            self, subscriber, mock_storage, device
        ):
            """on_device_register не трогает delete_device."""
            await subscriber.on_device_register(device)

            mock_storage.delete_device.assert_not_awaited()

    class TestOnDeviceStatusUpdate:
        """Тесты колбэка on_device_status_update."""

        @pytest.mark.asyncio
        async def test_calls_upsert_device(
            self,
            subscriber,
            mock_storage,
            device
        ):
            """on_device_status_update вызывает upsert_device."""
            old_status = DeviceStatus.OFFLINE
            new_status = DeviceStatus.ONLINE

            await subscriber.on_device_status_update(
                device,
                old_status,
                new_status
            )

            mock_storage.upsert_device.assert_awaited_once_with(device)

        @pytest.mark.asyncio
        async def test_calls_upsert_even_same_status(
            self, subscriber, mock_storage, device
        ):
            """
            Колбек всё равно вызывает upsert при совпадении статусов.

            Логика в subscriber.py не прерывает выполнение
            при одинаковом статусе — лишь логирует и продолжает.
            Upsert всё равно вызван.
            """
            status = DeviceStatus.ONLINE

            await subscriber.on_device_status_update(device, status, status)

            mock_storage.upsert_device.assert_awaited_once_with(device)

        @pytest.mark.asyncio
        async def test_does_not_raise_on_storage_error(
            self, subscriber, mock_storage, device
        ):
            """on_device_status_update не пробрасывает исключение."""
            mock_storage.upsert_device.side_effect = Exception(
                "connection lost"
            )

            await subscriber.on_device_status_update(
                device, DeviceStatus.OFFLINE, DeviceStatus.ONLINE
            )

        @pytest.mark.asyncio
        async def test_delete_not_called_on_status_update(
            self, subscriber, mock_storage, device
        ):
            """on_device_status_update не трогает delete_device."""
            await subscriber.on_device_status_update(
                device, DeviceStatus.OFFLINE, DeviceStatus.ONLINE
            )

            mock_storage.delete_device.assert_not_awaited()

    class TestOnDeviceUnregister:
        """Тесты колбэка on_device_unregister."""

        @pytest.mark.asyncio
        async def test_calls_delete_device(
            self,
            subscriber,
            mock_storage,
            device
        ):
            """on_device_unregister вызывает storage.delete_device."""
            await subscriber.on_device_unregister(device)

            mock_storage.delete_device.assert_awaited_once_with(
                device.device_id
            )

        @pytest.mark.asyncio
        async def test_does_not_raise_on_storage_error(
            self, subscriber, mock_storage, device
        ):
            """on_device_unregister не пробрасывает исключение при ошибке."""
            mock_storage.delete_device.side_effect = RuntimeError("DB gone")

            await subscriber.on_device_unregister(device)

        @pytest.mark.asyncio
        async def test_upsert_not_called_on_unregister(
            self, subscriber, mock_storage, device
        ):
            """on_device_unregister не трогает upsert_device."""
            await subscriber.on_device_unregister(device)

            mock_storage.upsert_device.assert_not_awaited()

        @pytest.mark.asyncio
        async def test_delete_called_with_correct_id(
            self,
            subscriber,
            mock_storage
        ):
            """on_device_unregister передаёт именно device_id устройства."""
            specific_device = Device(
                device_id="exact-id-999",
                name="Exact",
                device_type=DeviceType.ACTUATOR,
                device_status=DeviceStatus.OFFLINE,
                protocol=ProtocolType.MQTT,
            )

            await subscriber.on_device_unregister(specific_device)

            mock_storage.delete_device.assert_awaited_once_with("exact-id-999")
