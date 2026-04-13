"""Тест подписчика хранилища."""
import pytest
from unittest.mock import AsyncMock
from models.message import Message, MessageType
from models.telemetry import TelemetryRecord
from storage.subscriber import StorageSubscriber


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
