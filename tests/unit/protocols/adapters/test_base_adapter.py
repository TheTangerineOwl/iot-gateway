"""Тесты для ProtocolAdapter (базовый адаптер)."""
import asyncio
import pytest
import pytest_asyncio
from config.config import YAMLConfigLoader
from config.topics import TopicManager, TopicKey
from core.message_bus import MessageBus
from core.registry import DeviceRegistry
from models.message import Message
from models.device import ProtocolType
from protocols.adapters.base import ProtocolAdapter
from tests.conftest import drain, not_raises


class _StubAdapter(ProtocolAdapter):
    """Минимальная реализация ProtocolAdapter для тестирования."""

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.HTTP

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False


@pytest_asyncio.fixture
async def stub_adapter(
    config: YAMLConfigLoader,
    running_bus: MessageBus,
    registry: DeviceRegistry
):
    """Заглушка адаптера, подключённая к шине и реестру."""
    a = _StubAdapter(config)
    a.set_gateway_context(running_bus, registry)
    yield a


@pytest_asyncio.fixture
async def disconnected_adapter(config: YAMLConfigLoader):
    """Заглушка адаптера без подключения к шине."""
    return _StubAdapter(config)


class TestProtocolName:
    """Тесты свойства protocol_name."""

    @pytest.mark.unit
    def test_returns_protocol_type_value(self, stub_adapter: _StubAdapter):
        """protocol_name равен строковому значению protocol_type."""
        assert stub_adapter.protocol_name == ProtocolType.HTTP.value

    @pytest.mark.unit
    def test_name_is_string(self, stub_adapter: _StubAdapter):
        """protocol_name — строка."""
        assert isinstance(stub_adapter.protocol_name, str)


class TestIsRunning:
    """Тесты свойства is_running."""

    @pytest.mark.unit
    def test_initially_not_running(self, disconnected_adapter: _StubAdapter):
        """Новый адаптер по умолчанию не запущен."""
        assert disconnected_adapter.is_running is False

    @pytest.mark.unit
    async def test_running_after_start(self, stub_adapter: _StubAdapter):
        """После start() адаптер переходит в состояние running."""
        await stub_adapter.start()
        assert stub_adapter.is_running is True

    @pytest.mark.unit
    async def test_not_running_after_stop(self, stub_adapter: _StubAdapter):
        """После stop() адаптер выходит из состояния running."""
        await stub_adapter.start()
        await stub_adapter.stop()
        assert stub_adapter.is_running is False


class TestSetGatewayContext:
    """Тесты метода set_gateway_context."""

    @pytest.mark.unit
    def test_bus_assigned(
        self,
        stub_adapter: _StubAdapter,
        running_bus: MessageBus
    ):
        """После set_gateway_context шина доступна через _bus."""
        assert stub_adapter._bus is running_bus

    @pytest.mark.unit
    def test_registry_assigned(
        self,
        stub_adapter: _StubAdapter,
        registry: DeviceRegistry
    ):
        """После set_gateway_context реестр доступен через _registry."""
        assert stub_adapter._registry is registry

    @pytest.mark.unit
    def test_initially_no_bus(self, disconnected_adapter: _StubAdapter):
        """До set_gateway_context шина равна None."""
        assert disconnected_adapter._bus is None

    @pytest.mark.unit
    def test_initially_no_registry(self, disconnected_adapter: _StubAdapter):
        """До set_gateway_context реестр равен None."""
        assert disconnected_adapter._registry is None


class TestPublishMessage:
    """Тесты метода _publish_message."""

    @pytest.mark.unit
    async def test_publish_puts_message_on_bus(
        self,
        topics: TopicManager,
        stub_adapter: _StubAdapter,
        running_bus: MessageBus,
        message: Message
    ):
        """_publish_message помещает сообщение в очередь шины."""
        received: list[Message] = []

        async def _handler(m: Message) -> None:
            received.append(m)

        running_bus.subscribe(
            topics.get_subscription_pattern(
                TopicKey.DEVICES_TELEMETRY
            ),
            _handler
        )
        await stub_adapter._publish_message(
            topics.get(
                TopicKey.DEVICES_TELEMETRY,
                device_id=message.device_id
            ),
            message
        )
        await drain(running_bus)

        assert len(received) == 1
        assert received[0].message_id == message.message_id

    @pytest.mark.unit
    async def test_publish_sets_protocol(
        self,
        topics: TopicManager,
        stub_adapter: _StubAdapter,
        running_bus: MessageBus,
    ):
        """_publish_message проставляет protocol из адаптера в сообщение."""
        device_id = 'dev-unknown'
        msg = Message(
            device_id=device_id,
            protocol=ProtocolType.UNKNOWN,
        )
        received: list[Message] = []

        async def _handler(m: Message) -> None:
            received.append(m)

        running_bus.subscribe(
            topics.get_subscription_pattern(
                TopicKey.DEVICES_TELEMETRY
            ),
            _handler
        )
        await stub_adapter._publish_message(
            topics.get(
                TopicKey.DEVICES_TELEMETRY,
                device_id=msg.device_id
            ),
            msg
        )
        await drain(running_bus)

        assert received[0].protocol == ProtocolType.HTTP

    @pytest.mark.unit
    async def test_publish_without_bus_raises(
        self,
        disconnected_adapter: _StubAdapter,
        telemetry_message: Message
    ):
        """_publish_message без подключённой шины вызывает RuntimeError."""
        with pytest.raises(RuntimeError, match='not connected to message bus'):
            await disconnected_adapter._publish_message(
                'test.topic',
                telemetry_message
            )


class TestRegisterPending:
    """Тесты метода _register_pending."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_future_is_stored(
        self,
        stub_adapter: _StubAdapter,
        telemetry_message: Message
    ):
        """_register_pending сохраняет Future в _pending по message_id."""
        fut = stub_adapter._register_pending(telemetry_message)
        assert telemetry_message.message_id in stub_adapter._pending
        assert stub_adapter._pending[telemetry_message.message_id] is fut

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_future(
        self,
        stub_adapter: _StubAdapter,
        telemetry_message: Message
    ):
        """_register_pending возвращает asyncio.Future."""
        fut = stub_adapter._register_pending(telemetry_message)
        assert isinstance(fut, asyncio.Future)


class TestHandleRejectedBase:
    """Тесты метода _handle_rejected_base."""

    @pytest.mark.unit
    async def test_resolves_pending_future(
        self,
        stub_adapter: _StubAdapter,
        telemetry_message: Message
    ):
        """_handle_rejected_base завершает зарегистрированный Future."""
        fut = stub_adapter._register_pending(telemetry_message)

        await stub_adapter._handle_rejected_base(telemetry_message)
        assert fut.done()
        assert fut.result() is telemetry_message

    @pytest.mark.unit
    async def test_removes_from_pending(
        self,
        stub_adapter: _StubAdapter,
        telemetry_message: Message
    ):
        """_handle_rejected_base удаляет Future из _pending."""
        stub_adapter._register_pending(telemetry_message)

        await stub_adapter._handle_rejected_base(telemetry_message)
        assert telemetry_message.message_id not in stub_adapter._pending

    @pytest.mark.unit
    async def test_unknown_message_id_is_noop(
        self, stub_adapter: _StubAdapter, telemetry_message: Message
    ):
        """_handle_rejected_base с неизвестным message_id ничего не делает."""
        telemetry_message.message_id = 'unknown-id'
        with not_raises(Exception):
            await stub_adapter._handle_rejected_base(telemetry_message)

    @pytest.mark.unit
    async def test_already_done_future_is_skipped(
        self, stub_adapter: _StubAdapter, telemetry_message: Message
    ):
        """_handle_rejected_base не ставит в уже завершённый Future."""
        fut = stub_adapter._register_pending(telemetry_message)
        fut.cancel()

        with not_raises(Exception):
            await stub_adapter._handle_rejected_base(telemetry_message)


class TestHealthCheck:
    """Тесты метода _health_check."""

    @pytest.mark.unit
    async def test_health_contains_protocol(self, stub_adapter: _StubAdapter):
        """_health_check возвращает словарь с ключом 'protocol'."""
        health = await stub_adapter._health_check()
        assert 'protocol' in health

    @pytest.mark.unit
    async def test_health_protocol_value(self, stub_adapter: _StubAdapter):
        """_health_check возвращает верное имя протокола."""
        health = await stub_adapter._health_check()
        assert health['protocol'] == ProtocolType.HTTP.value

    @pytest.mark.unit
    async def test_health_contains_running(self, stub_adapter: _StubAdapter):
        """_health_check возвращает словарь с ключом 'running'."""
        health = await stub_adapter._health_check()
        assert 'running' in health

    @pytest.mark.unit
    async def test_health_running_reflects_state(
        self, stub_adapter: _StubAdapter
    ):
        """_health_check['running'] отражает реальное состояние адаптера."""
        await stub_adapter.start()
        health = await stub_adapter._health_check()
        assert health['running'] is True

        await stub_adapter.stop()
        health = await stub_adapter._health_check()
        assert health['running'] is False
