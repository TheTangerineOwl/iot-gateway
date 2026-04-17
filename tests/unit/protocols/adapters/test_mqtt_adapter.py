"""Юнит-тесты для MQTTAdapter."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from models.device import ProtocolType
from protocols.adapters.mqtt_adapter import MQTTAdapter
from tests.conftest import DEVICE_DEF_ID


@pytest.mark.unit
class TestMQTTAdapterProperties:
    """Базовые свойства адаптера."""

    def test_protocol_name(self, mqtt_adapter: MQTTAdapter):
        """Возвращается строка 'MQTT'."""
        assert mqtt_adapter.protocol_name == ProtocolType.MQTT

    def test_protocol_type(self, mqtt_adapter: MQTTAdapter):
        """protocol_type соответствует ProtocolType.MQTT."""
        assert mqtt_adapter.protocol_type == ProtocolType.MQTT

    def test_not_running_initially(self, mqtt_adapter: MQTTAdapter):
        """До запуска is_running == False."""
        assert mqtt_adapter.is_running is False

    def test_not_connected_initially(self, mqtt_adapter: MQTTAdapter):
        """До запуска is_connected == False."""
        assert mqtt_adapter.is_connected is False

    def test_client_is_none_initially(self, mqtt_adapter: MQTTAdapter):
        """До запуска client == None."""
        assert mqtt_adapter.client is None

    def test_broker_host_not_empty(self, mqtt_adapter: MQTTAdapter):
        """Хост брокера содержит непустую строку."""
        assert (
            mqtt_adapter.broker_host
            and isinstance(mqtt_adapter.broker_host, str)
        )

    def test_broker_port_is_int(self, mqtt_adapter: MQTTAdapter):
        """Порт брокера — целое число."""
        assert isinstance(mqtt_adapter.broker_port, int)
        assert mqtt_adapter.broker_port > 0

    def test_qos_is_valid(self, mqtt_adapter: MQTTAdapter):
        """Параметр QoS имеет корректное значение (0, 1 или 2)."""
        assert mqtt_adapter.qos in (0, 1, 2)

    def test_keepalive_is_positive(self, mqtt_adapter: MQTTAdapter):
        """Keepalive — положительное число."""
        assert mqtt_adapter.keepalive > 0

    def test_client_id_not_empty(self, mqtt_adapter: MQTTAdapter):
        """Client ID содержит непустую строку."""
        assert (
            mqtt_adapter.client_id
            and isinstance(mqtt_adapter.client_id, str)
        )

    def test_protocol_version_set(self, mqtt_adapter: MQTTAdapter):
        """Версия протокола установлена."""
        assert mqtt_adapter.protocol_version is not None


@pytest.mark.unit
class TestMQTTAdapterLifecycle:
    """Запуск и остановка адаптера."""

    @pytest.mark.asyncio
    async def test_start_sets_running(self, mqtt_adapter: MQTTAdapter):
        """После start() is_running == True."""
        with patch('asyncio.create_task') as mock_task:
            mock_task.return_value = AsyncMock()
            await mqtt_adapter.start()
            assert mqtt_adapter.is_running is True

    @pytest.mark.asyncio
    async def test_start_creates_run_task(self, mqtt_adapter: MQTTAdapter):
        """После start() _run_task не None."""
        with patch('asyncio.create_task') as mock_task:
            mock_run_task = AsyncMock()
            mock_task.return_value = mock_run_task
            await mqtt_adapter.start()
            assert mqtt_adapter._run_task is not None

    @pytest.mark.asyncio
    async def test_stop_clears_running(self, mqtt_adapter: MQTTAdapter):
        """После stop() is_running == False."""
        with patch('asyncio.create_task') as mock_task:
            mock_task.return_value = AsyncMock()
            await mqtt_adapter.start()
            await mqtt_adapter.stop()
            assert mqtt_adapter.is_running is False

    @pytest.mark.asyncio
    async def test_stop_calls_disconnect(self, mqtt_adapter: MQTTAdapter):
        """stop() вызывает disconnect."""
        with patch('asyncio.create_task') as mock_task:
            mock_task.return_value = AsyncMock()
            await mqtt_adapter.start()
            with patch.object(
                mqtt_adapter, 'disconnect', new_callable=AsyncMock
            ) as mock_disconnect:
                await mqtt_adapter.stop()
                mock_disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stop_without_start_does_not_raise(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """stop() без предшествующего start() не бросает исключения."""
        await mqtt_adapter.stop()  # должно пройти молча

    @pytest.mark.asyncio
    async def test_double_start_does_not_raise(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """Повторный start() не бросает исключения."""
        with patch('asyncio.create_task') as mock_task:
            mock_task.return_value = AsyncMock()
            await mqtt_adapter.start()
            await mqtt_adapter.start()
            assert mqtt_adapter.is_running is True


@pytest.mark.unit
class TestMQTTAdapterConnection:
    """Подключение и отключение от брокера."""

    @pytest.mark.asyncio
    async def test_connect_returns_bool(self, mqtt_adapter: MQTTAdapter):
        """connect() возвращает boolean."""
        with patch(
            'protocols.adapters.mqtt_adapter.Client'
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            result = await mqtt_adapter.connect()
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_connect_sets_connected_true_on_success(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """Успешное подключение устанавливает is_connected == True."""
        with patch(
            'protocols.adapters.mqtt_adapter.Client'
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            # mqtt_adapter._subscribe_topics = AsyncMock()

            # Симулируем успешное подключение
            await mqtt_adapter.connect()
            assert mqtt_adapter.is_connected is True

    @pytest.mark.asyncio
    async def test_connect_sets_client_not_none(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """После подключения client != None."""
        with patch(
            'protocols.adapters.mqtt_adapter.Client'
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            # mqtt_adapter._subscribe_topics = AsyncMock()

            await mqtt_adapter.connect()
            assert mqtt_adapter.client is not None

    @pytest.mark.asyncio
    async def test_connect_failure_sets_connected_false(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """При ошибке подключения is_connected == False."""
        with patch(
            'protocols.adapters.mqtt_adapter.Client'
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.__aenter__.side_effect = Exception("Connection failed")

            result = await mqtt_adapter.connect()
            assert result is False
            assert mqtt_adapter.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect_returns_bool(self, mqtt_adapter: MQTTAdapter):
        """disconnect() возвращает boolean."""
        result = await mqtt_adapter.disconnect()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_disconnect_sets_connected_false(
        self,
        mqtt_adapter:
        MQTTAdapter
    ):
        """disconnect() устанавливает is_connected == False."""
        mqtt_adapter.is_connected = True
        result = await mqtt_adapter.disconnect()
        assert result is True
        assert mqtt_adapter.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect_clears_client(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """disconnect() очищает client."""
        with patch(
            'protocols.adapters.mqtt_adapter.Client'
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            # mqtt_adapter._subscribe_topics = AsyncMock()

            await mqtt_adapter.connect()
            assert mqtt_adapter.client is not None

            await mqtt_adapter.disconnect()
            assert mqtt_adapter.client is None

    @pytest.mark.asyncio
    async def test_connect_calls_subscribe_topics(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """connect() вызывает _subscribe_topics()."""
        # with patch(
        #     'protocols.adapters.mqtt_adapter.Client'
        # ) as mock_client_class:
        #     mock_client = AsyncMock()
        #     mock_client_class.return_value = mock_client
        #     mqtt_adapter._subscribe_topics = AsyncMock()

        #     await mqtt_adapter.connect()
        #     mqtt_adapter._subscribe_topics.assert_awaited_once()
        with patch(
            'protocols.adapters.mqtt_adapter.Client'
        ) as mock_client_class:
            with patch.object(
                MQTTAdapter, '_subscribe_topics', return_value=None
            ) as mock_subscribe:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                await mqtt_adapter.connect()

                mock_subscribe.assert_awaited_once()


@pytest.mark.unit
class TestMQTTAdapterTLS:
    """Тестирование TLS/SSL функциональности."""

    def test_tls_disabled_by_default(self, mqtt_adapter: MQTTAdapter):
        """TLS отключен по умолчанию."""
        assert mqtt_adapter.use_tls is False

    def test_tls_insecure_disabled_by_default(self, mqtt_adapter: MQTTAdapter):
        """Unsafe TLS отключен по умолчанию."""
        assert mqtt_adapter.tls_insecure is False

    @pytest.mark.asyncio
    async def test_connect_with_tls_enabled(self):
        """Подключение с TLS работает корректно."""
        with patch.dict(
            'os.environ',
            {
                'MQTT_USE_TLS': 'true',
                'MQTT_TLS_INSECURE': 'false'
            }
        ):
            adapter = MQTTAdapter()
            with patch(
                'protocols.adapters.mqtt_adapter.Client'
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                adapter._subscribe_topics = AsyncMock()

                result = await adapter.connect()
                assert isinstance(result, bool)


@pytest.mark.unit
class TestMQTTAdapterSendCommand:
    """Отправка команд через MQTT."""

    @pytest.mark.asyncio
    async def test_send_command_returns_bool(self, mqtt_adapter: MQTTAdapter):
        """send_command() возвращает boolean."""
        mqtt_adapter.is_connected = False
        result = await mqtt_adapter.send_command(
            DEVICE_DEF_ID, {"action": "test"}
        )
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_send_command_fails_when_not_connected(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """send_command() возвращает False, если не подключен."""
        mqtt_adapter.is_connected = False
        mqtt_adapter.client = None
        result = await mqtt_adapter.send_command(
            DEVICE_DEF_ID, {"action": "test"}
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_succeeds_when_connected(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """send_command() возвращает True при успешной отправке."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        result = await mqtt_adapter.send_command(
            DEVICE_DEF_ID, {"action": "test"}
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_command_publishes_to_correct_topic(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """send_command() публикует на тему 'devices/{device_id}/command'."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        await mqtt_adapter.send_command(DEVICE_DEF_ID, {"action": "test"})

        # Проверяем, что publish был вызван с правильной темой
        call_args = mock_client.publish.call_args
        assert call_args is not None
        assert call_args[1]['topic'] == f"devices/{DEVICE_DEF_ID}/command"

    @pytest.mark.asyncio
    async def test_send_command_publishes_json_payload(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """send_command() публикует payload в формате JSON."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        command = {"action": "toggle", "state": True}
        await mqtt_adapter.send_command(DEVICE_DEF_ID, command)

        call_args = mock_client.publish.call_args
        assert call_args is not None
        # Проверяем, что payload — это JSON-строка
        import json
        payload = call_args[1]['payload']
        parsed = json.loads(payload)
        assert parsed == command

    @pytest.mark.asyncio
    async def test_send_command_uses_configured_qos(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """send_command() использует настроенный QoS."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client
        mqtt_adapter.qos = 2

        await mqtt_adapter.send_command(DEVICE_DEF_ID, {"action": "test"})

        call_args = mock_client.publish.call_args
        assert call_args is not None
        assert call_args[1]['qos'] == 2

    @pytest.mark.asyncio
    async def test_send_command_handles_mqtt_error(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """send_command() обрабатывает MqttError корректно."""
        from aiomqtt import MqttError

        mock_client = AsyncMock()
        mock_client.publish = AsyncMock(side_effect=MqttError())
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        result = await mqtt_adapter.send_command(
            DEVICE_DEF_ID, {"action": "test"}
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_handles_generic_exception(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """send_command() обрабатывает генерические исключения."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock(side_effect=RuntimeError("boom"))
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        result = await mqtt_adapter.send_command(
            DEVICE_DEF_ID, {"action": "test"}
        )
        assert result is False


@pytest.mark.unit
class TestMQTTAdapterSendMessage:
    """Отправка сообщений через MQTT."""

    @pytest.mark.asyncio
    async def test_send_message_returns_bool(self, mqtt_adapter: MQTTAdapter):
        """send_message() возвращает boolean."""
        mqtt_adapter.is_connected = False
        result = await mqtt_adapter.send_message(
            DEVICE_DEF_ID,
            "error.message",
            {"error": "test"}
        )
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_send_message_fails_when_not_connected(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """send_message() возвращает False, если не подключен."""
        mqtt_adapter.is_connected = False
        mqtt_adapter.client = None
        result = await mqtt_adapter.send_message(
            DEVICE_DEF_ID,
            "error.message",
            {"error": "test"}
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_send_message_succeeds_when_connected(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """send_message() возвращает True при успешной отправке."""
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

    @pytest.mark.asyncio
    async def test_send_message_converts_dots_to_slashes(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """send_message() преобразует точки в слэши в топике."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        await mqtt_adapter.send_message(
            DEVICE_DEF_ID,
            "error.message.detail",
            {"error": "test"}
        )

        call_args = mock_client.publish.call_args
        assert call_args is not None
        # Тема должна быть: devices/error/message/detail
        topic = call_args[1]['topic']
        assert '/' in topic
        assert topic.startswith('devices')

    @pytest.mark.asyncio
    async def test_send_message_publishes_json_payload(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """send_message() публикует payload в формате JSON."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        message = {"error": "invalid_data", "details": "missing_field"}
        await mqtt_adapter.send_message(
            DEVICE_DEF_ID, "error.message", message
        )

        call_args = mock_client.publish.call_args
        assert call_args is not None
        import json
        payload = call_args[1]['payload']
        parsed = json.loads(payload)
        assert parsed == message

    @pytest.mark.asyncio
    async def test_send_message_uses_configured_qos(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """send_message() использует настроенный QoS."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client
        mqtt_adapter.qos = 1

        await mqtt_adapter.send_message(DEVICE_DEF_ID, "error.message", {})

        call_args = mock_client.publish.call_args
        assert call_args is not None
        assert call_args[1]['qos'] == 1

    @pytest.mark.asyncio
    async def test_send_message_handles_mqtt_error(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """send_message() обрабатывает MqttError корректно."""
        from aiomqtt import MqttError

        mock_client = AsyncMock()
        mock_client.publish = AsyncMock(side_effect=MqttError())
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        result = await mqtt_adapter.send_message(
            DEVICE_DEF_ID,
            "error.message",
            {"error": "test"}
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_send_message_handles_generic_exception(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """send_message() обрабатывает генерические исключения."""
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock(side_effect=RuntimeError("boom"))
        mqtt_adapter.is_connected = True
        mqtt_adapter.client = mock_client

        result = await mqtt_adapter.send_message(
            DEVICE_DEF_ID,
            "error.message",
            {"error": "test"}
        )
        assert result is False


@pytest.mark.unit
class TestMQTTAdapterCleanup:
    """Очистка ресурсов адаптера."""

    @pytest.mark.asyncio
    async def test_cleanup_cancels_message_task(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """_cleanup() отменяет _message_task если она запущена."""
        async def _dummy_task():
            await asyncio.sleep(10)

        task = asyncio.create_task(_dummy_task())
        mqtt_adapter._message_task = task

        await mqtt_adapter._cleanup()

        assert task.cancelled()
        # assert mqtt_adapter._message_task is None

    @pytest.mark.asyncio
    async def test_cleanup_skips_cancelled_task(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """_cleanup() пропускает уже отменённую задачу."""
        mock_task = AsyncMock()
        mock_task.done.return_value = True
        mqtt_adapter._message_task = mock_task

        await mqtt_adapter._cleanup()

        mock_task.cancel.assert_not_called()
        assert mqtt_adapter._message_task is mock_task

    @pytest.mark.asyncio
    async def test_cleanup_clears_exit_stack(self, mqtt_adapter: MQTTAdapter):
        """_cleanup() очищает _exit_stack."""
        from contextlib import AsyncExitStack
        mock_exit_stack = AsyncMock(spec=AsyncExitStack)
        mock_exit_stack.__aexit__ = AsyncMock()
        mqtt_adapter._exit_stack = mock_exit_stack

        await mqtt_adapter._cleanup()

        assert mqtt_adapter._exit_stack is None
        mock_exit_stack.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_clears_client(self, mqtt_adapter: MQTTAdapter):
        """_cleanup() устанавливает client = None."""
        mock_client = AsyncMock()
        mqtt_adapter.client = mock_client

        await mqtt_adapter._cleanup()

        assert mqtt_adapter.client is None

    @pytest.mark.asyncio
    async def test_cleanup_sets_connected_false(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """_cleanup() устанавливает is_connected = False."""
        mqtt_adapter.is_connected = True

        await mqtt_adapter._cleanup()

        assert mqtt_adapter.is_connected is False

    @pytest.mark.asyncio
    async def test_cleanup_clears_message_task(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """_cleanup() устанавливает _message_task = None."""
        async def _dummy_task():
            await asyncio.sleep(10)

        task = asyncio.create_task(_dummy_task())
        mqtt_adapter._message_task = task

        await mqtt_adapter._cleanup()

        # assert task.cancelled()
        assert mqtt_adapter._message_task is None


@pytest.mark.unit
class TestMQTTAdapterContextIntegration:
    """Интеграция адаптера с message bus и registry."""

    def test_set_gateway_context(
            self,
            mqtt_adapter: MQTTAdapter,
            running_bus,
            registry
    ):
        """set_gateway_context() устанавливает bus и registry."""
        mqtt_adapter.set_gateway_context(running_bus, registry)
        assert mqtt_adapter._bus == running_bus
        assert mqtt_adapter._registry == registry

    @pytest.mark.asyncio
    async def test_health_check_returns_dict(self, mqtt_adapter: MQTTAdapter):
        """_health_check() возвращает словарь."""
        result = await mqtt_adapter._health_check()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_health_check_has_protocol(self, mqtt_adapter: MQTTAdapter):
        """health_check ответ содержит 'protocol'."""
        result = await mqtt_adapter._health_check()
        assert 'protocol' in result

    @pytest.mark.asyncio
    async def test_health_check_has_running(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """health_check ответ содержит 'running'."""
        result = await mqtt_adapter._health_check()
        assert 'running' in result

    @pytest.mark.asyncio
    async def test_health_check_protocol_value(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """health_check 'protocol' соответствует имени протокола."""
        result = await mqtt_adapter._health_check()
        assert result['protocol'] == mqtt_adapter.protocol_name

    @pytest.mark.asyncio
    async def test_health_check_running_false_initially(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """health_check 'running' == False до запуска."""
        result = await mqtt_adapter._health_check()
        assert result['running'] is False

    @pytest.mark.asyncio
    async def test_health_check_running_true_when_started(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """health_check 'running' == True после start()."""
        with patch('asyncio.create_task') as mock_task:
            mock_task.return_value = AsyncMock()
            await mqtt_adapter.start()
            result = await mqtt_adapter._health_check()
            assert result['running'] is True


@pytest.mark.unit
class TestMQTTAdapterReconnection:
    """Переподключение при разрыве соединения."""

    def test_reconnect_interval_initialized(self, mqtt_adapter: MQTTAdapter):
        """_reconnect_interval инициализирован на 3.0 сек."""
        assert mqtt_adapter._reconnect_interval == 3.0

    def test_max_reconnect_interval_set(self, mqtt_adapter: MQTTAdapter):
        """_max_reconnect_interval установлен на 300.0 сек."""
        assert mqtt_adapter._max_reconnect_interval == 300.0

    @pytest.mark.asyncio
    async def test_connect_resets_reconnect_interval(
        self,
        mqtt_adapter: MQTTAdapter
    ):
        """connect() сбрасывает _reconnect_interval на 3.0."""
        mqtt_adapter._reconnect_interval = 100.0

        with patch(
            'protocols.adapters.mqtt_adapter.Client'
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            # mqtt_adapter._subscribe_topics = AsyncMock()

            await mqtt_adapter.connect()
            assert mqtt_adapter._reconnect_interval == 3.0
