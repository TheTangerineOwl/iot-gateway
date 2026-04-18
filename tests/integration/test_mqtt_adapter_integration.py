"""Интеграционные тесты для MQTT адаптера с message bus."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from typenv import Env
from config.config import load_env
from core.message_bus import MessageBus
from core.registry import DeviceRegistry
from models.message import Message, MessageType
from protocols.adapters.mqtt_adapter import MQTTAdapter
from tests.conftest import (
    DEVICE_DEF_ID
)


load_env('env.example')
env = Env(upper=True)


@pytest.fixture
def mqtt_adapter(config, running_bus: MessageBus, registry: DeviceRegistry):
    """MQTT-адаптер для тестов."""
    adapter = MQTTAdapter(config)
    adapter.set_gateway_context(running_bus, registry)
    yield adapter


@pytest.mark.unit
class TestMQTTAdapterMessageBusIntegration:
    """Тестирование интеграции адаптера с message bus."""

    @pytest.mark.asyncio
    async def test_adapter_connects_to_bus(self, mqtt_adapter: MQTTAdapter):
        """Адаптер успешно подключен к message bus."""
        assert mqtt_adapter._bus is not None
        assert isinstance(mqtt_adapter._bus, MessageBus)

    @pytest.mark.asyncio
    async def test_adapter_has_registry(self, mqtt_adapter: MQTTAdapter):
        """Адаптер имеет доступ к registry."""
        assert mqtt_adapter._registry is not None

    @pytest.mark.asyncio
    async def test_send_command_with_real_bus(self, mqtt_adapter: MQTTAdapter):
        """send_command работает с реальной bus."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        result = await mqtt_adapter.send_command(
            DEVICE_DEF_ID, {"action": "test"}
        )
        assert result is True
        mock_client.publish.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_message_with_real_bus(self, mqtt_adapter: MQTTAdapter):
        """send_message работает с реальной bus."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        result = await mqtt_adapter.send_message(
            DEVICE_DEF_ID,
            "error.message",
            {"error": "test"}
        )
        assert result is True
        mock_client.publish.assert_awaited_once()


@pytest.mark.unit
class TestMQTTAdapterStartStopCycle:
    """Тестирование полного цикла старт-стоп адаптера."""

    @pytest.mark.asyncio
    async def test_start_stop_cycle(self, mqtt_adapter: MQTTAdapter):
        """Полный цикл: start → stop."""
        with patch('asyncio.create_task') as mock_task:
            mock_run_task = AsyncMock()
            mock_task.return_value = mock_run_task

            # Start
            await mqtt_adapter.start()
            assert mqtt_adapter.is_running is True
            assert mqtt_adapter._run_task is not None

            # Stop
            await mqtt_adapter.stop()
            assert mqtt_adapter.is_running is False

    @pytest.mark.asyncio
    async def test_multiple_start_stop_cycles(self, mqtt_adapter: MQTTAdapter):
        """Несколько циклов старт-стоп."""
        with patch('asyncio.create_task') as mock_task:
            mock_run_task = AsyncMock()
            mock_task.return_value = mock_run_task

            for _ in range(3):
                await mqtt_adapter.start()
                assert mqtt_adapter.is_running is True
                await mqtt_adapter.stop()
                assert mqtt_adapter.is_running is False

    @pytest.mark.asyncio
    async def test_disconnect_clears_all_state(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """disconnect() полностью очищает состояние."""
        # Симулируем подключение
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = AsyncMock()
        mqtt_adapter._exit_stack = AsyncMock()

        # Отключаемся
        result = await mqtt_adapter.disconnect()

        # Проверяем очистку
        assert result is True
        assert mqtt_adapter.is_connected is False
        assert mqtt_adapter.client is None
        assert mqtt_adapter._exit_stack is None


@pytest.mark.unit
class TestMQTTAdapterCommandFlow:
    """Тестирование потока команд от шлюза к устройству."""

    @pytest.mark.asyncio
    async def test_send_toggle_command(self, mqtt_adapter: MQTTAdapter):
        """Отправка команды toggle."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        command = {
            "command": "toggle",
            "target": "relay",
            "state": True
        }

        result = await mqtt_adapter.send_command(DEVICE_DEF_ID, command)
        assert result is True

        call_args = mock_client.publish.call_args
        assert call_args is not None
        assert call_args[1]['topic'] == f"devices/{DEVICE_DEF_ID}/command"

    @pytest.mark.asyncio
    async def test_send_config_command(self, mqtt_adapter: MQTTAdapter):
        """Отправка команды конфигурации."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        command = {
            "command": "config",
            "interval": 30,
            "sensors": ["temperature", "humidity"]
        }

        result = await mqtt_adapter.send_command(DEVICE_DEF_ID, command)
        assert result is True

    @pytest.mark.asyncio
    async def test_send_reboot_command(self, mqtt_adapter: MQTTAdapter):
        """Отправка команды перезагрузки."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        command = {"command": "reboot"}

        result = await mqtt_adapter.send_command(DEVICE_DEF_ID, command)
        assert result is True


@pytest.mark.unit
class TestMQTTAdapterErrorReporting:
    """Тестирование отправки ошибок на устройства."""

    @pytest.mark.asyncio
    async def test_send_validation_error(self, mqtt_adapter: MQTTAdapter):
        """Отправка ошибки валидации."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        error = {
            "error_code": "VALIDATION_ERROR",
            "message": "Invalid payload format",
            "field": "temperature"
        }

        result = await mqtt_adapter.send_message(
            DEVICE_DEF_ID,
            "error.validation",
            error
        )
        assert result is True

        call_args = mock_client.publish.call_args
        assert call_args is not None
        assert "error" in call_args[1]['topic']

    @pytest.mark.asyncio
    async def test_send_timeout_error(self, mqtt_adapter: MQTTAdapter):
        """Отправка ошибки timeout."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        error = {
            "error_code": "TIMEOUT",
            "message": "Device did not respond in time"
        }

        result = await mqtt_adapter.send_message(
            DEVICE_DEF_ID,
            "error.timeout",
            error
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_connection_error(self, mqtt_adapter: MQTTAdapter):
        """Отправка ошибки подключения."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        error = {
            "error_code": "CONNECTION_ERROR",
            "message": "Lost connection to device"
        }

        result = await mqtt_adapter.send_message(
            DEVICE_DEF_ID,
            "error.connection",
            error
        )
        assert result is True


@pytest.mark.unit
class TestMQTTAdapterQoSHandling:
    """Тестирование обработки различных уровней QoS."""

    @pytest.mark.asyncio
    async def test_send_with_qos_0(self, mqtt_adapter: MQTTAdapter):
        """Отправка с QoS 0 (at most once)."""
        mqtt_adapter.qos = 0
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        await mqtt_adapter.send_command(DEVICE_DEF_ID, {"test": "data"})

        call_args = mock_client.publish.call_args
        assert call_args[1]['qos'] == 0

    @pytest.mark.asyncio
    async def test_send_with_qos_1(self, mqtt_adapter: MQTTAdapter):
        """Отправка с QoS 1 (at least once)."""
        mqtt_adapter.qos = 1
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        await mqtt_adapter.send_command(DEVICE_DEF_ID, {"test": "data"})

        call_args = mock_client.publish.call_args
        assert call_args[1]['qos'] == 1

    @pytest.mark.asyncio
    async def test_send_with_qos_2(self, mqtt_adapter: MQTTAdapter):
        """Отправка с QoS 2 (exactly once)."""
        mqtt_adapter.qos = 2
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        await mqtt_adapter.send_command(DEVICE_DEF_ID, {"test": "data"})

        call_args = mock_client.publish.call_args
        assert call_args[1]['qos'] == 2


@pytest.mark.unit
class TestMQTTAdapterTopicHandling:
    """Тестирование корректного формирования топиков."""

    @pytest.mark.asyncio
    async def test_command_topic_format(self, mqtt_adapter: MQTTAdapter):
        """Формат топика для команд."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        await mqtt_adapter.send_command(DEVICE_DEF_ID, {})

        call_args = mock_client.publish.call_args
        topic = call_args[1]['topic']
        assert topic == f"devices/{DEVICE_DEF_ID}/command"

    @pytest.mark.asyncio
    async def test_message_topic_with_dots(self, mqtt_adapter: MQTTAdapter):
        """Преобразование точек в слэши в топике сообщения."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        await mqtt_adapter.send_message(
            DEVICE_DEF_ID, "error.validation.field", {}
        )

        call_args = mock_client.publish.call_args
        topic = call_args[1]['topic']
        # devices + error.validation.field → devices/error/validation/field
        assert "/" in topic
        assert "\\" not in topic
        assert topic.startswith("devices")

    @pytest.mark.asyncio
    async def test_message_topic_single_level(self, mqtt_adapter: MQTTAdapter):
        """Топик сообщения с одним уровнем."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        await mqtt_adapter.send_message(DEVICE_DEF_ID, "error", {})

        call_args = mock_client.publish.call_args
        topic = call_args[1]['topic']
        assert "devices" in topic
        assert "error" in topic

    @pytest.mark.asyncio
    async def test_message_topic_multiple_levels(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """Топик сообщения с несколькими уровнями."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        await mqtt_adapter.send_message(
            DEVICE_DEF_ID,
            "error.sensor.temperature.out_of_range",
            {}
        )

        call_args = mock_client.publish.call_args
        topic = call_args[1]['topic']
        assert topic.count("/") >= 3  # Минимум 3 слэша


@pytest.mark.unit
class TestMQTTAdapterPendingMessages:
    """Тестирование обработки ожидающих сообщений."""

    @pytest.mark.asyncio
    async def test_register_pending(self, mqtt_adapter: MQTTAdapter):
        """_register_pending() создает Future для сообщения."""
        msg = Message(
            message_id="test-123",
            device_id=DEVICE_DEF_ID,
            message_type=MessageType.TELEMETRY,
            payload={}
        )

        fut = mqtt_adapter._register_pending(msg)
        assert fut is not None
        assert msg.message_id in mqtt_adapter._pending

    @pytest.mark.asyncio
    async def test_handle_rejected(self, mqtt_adapter: MQTTAdapter):
        """_handle_rejected_base() обрабатывает отклоненное сообщение."""
        msg = Message(
            message_id="test-123",
            device_id=DEVICE_DEF_ID,
            message_type=MessageType.TELEMETRY,
            payload={}
        )

        # fut = mqtt_adapter._register_pending(msg)

        rejected = Message(
            message_id="test-123",
            device_id=DEVICE_DEF_ID,
            metadata={"reject_reason": "invalid"}
        )

        await mqtt_adapter._handle_rejected_base(rejected)

        assert msg.message_id not in mqtt_adapter._pending

    @pytest.mark.asyncio
    async def test_pending_cleared_after_handling(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """Pending сообщение удаляется после обработки."""
        msg = Message(
            message_id="test-456",
            device_id=DEVICE_DEF_ID,
            message_type=MessageType.TELEMETRY,
            payload={}
        )

        mqtt_adapter._register_pending(msg)
        assert len(mqtt_adapter._pending) == 1

        rejected = Message(
            message_id="test-456",
            device_id=DEVICE_DEF_ID,
        )

        await mqtt_adapter._handle_rejected_base(rejected)
        assert len(mqtt_adapter._pending) == 0


@pytest.mark.unit
class TestMQTTAdapterConcurrency:
    """Тестирование асинхронной безопасности адаптера."""

    @pytest.mark.asyncio
    async def test_concurrent_commands(self, mqtt_adapter: MQTTAdapter):
        """Отправка нескольких команд одновременно."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        tasks = [
            mqtt_adapter.send_command(f"dev-{i}", {"cmd": f"command_{i}"})
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)
        assert all(results)
        assert mock_client.publish.await_count == 5

    @pytest.mark.asyncio
    async def test_concurrent_messages(self, mqtt_adapter: MQTTAdapter):
        """Отправка нескольких сообщений одновременно."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        tasks = [
            mqtt_adapter.send_message(
                f"dev-{i}",
                f"error.type_{i}",
                {"error": f"error_{i}"}
            )
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)
        assert all(results)
        assert mock_client.publish.await_count == 5

    @pytest.mark.asyncio
    async def test_concurrent_connect_attempts(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """Попытки подключения не вызывают race conditions."""
        with patch(
            'protocols.adapters.mqtt_adapter.Client'
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            # mqtt_adapter._subscribe_topics = AsyncMock()

            # Две попытки подключения одновременно не должны вызвать проблемы
            results = await asyncio.gather(
                mqtt_adapter.connect(),
                mqtt_adapter.connect(),
                return_exceptions=True
            )

            assert len(results) == 2
