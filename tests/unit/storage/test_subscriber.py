"""Тест подписчика хранилища."""
import pytest
from storage.subscriber import StorageSubscriber


@pytest.mark.asyncio
async def test_handle_saves_record(mock_storage, telemetry_message):
    """StorageSubscriber.handle вызывает storage.save с корректной записью."""
    subscriber = StorageSubscriber(mock_storage)
    telemetry_message.processed = True

    await subscriber.handle(telemetry_message)

    mock_storage.save.assert_awaited_once()
    saved_record = mock_storage.save.call_args[0][0]
    assert saved_record.device_id == "dev-001"
    assert saved_record.payload == {"temp": 42.0}


@pytest.mark.asyncio
async def test_handle_storage_error(
    mock_storage,
    telemetry_message
):
    """Шина должна оставаться живой."""
    mock_storage.save.side_effect = Exception("Test storage error")
    subscriber = StorageSubscriber(mock_storage)

    await subscriber.handle(telemetry_message)
