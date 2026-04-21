"""Основной модуль шлюза."""
import asyncio
import logging
import signal
from typing import Any
from config.config import get_conf, YAMLConfigLoader
from config.topics import TopicKey
from core.registry import DeviceRegistry
from core.message_bus import MessageBus
from core.pipeline.pipeline import Pipeline
from core.pipeline.stages import (
    ValidationStage, AuthorizationStage, CleanupStage
)
from models.device import DeviceStatus, Device, ProtocolType
from models.message import Message, MessageType
from storage.base import StorageBase
from storage.sqlite import SQLiteStorage
from storage.postgresql import PostgresStorage
from storage.subscriber import StorageSubscriber
from protocols.adapters.base import ProtocolAdapter
from protocols.adapters.coap_adapter import CoAPAdapter
from protocols.adapters.http_adapter import HTTPAdapter
from protocols.adapters.websocket_adapter import WebSocketAdapter
from protocols.adapters.mqtt_adapter import MQTTAdapter

# env = Env(upper=True)
logger = logging.getLogger(__name__)


class Gateway:
    """Основной модуль работы шлюза."""

    def __init__(self, config: YAMLConfigLoader) -> None:
        """Основной модуль работы шлюза."""
        self._config = config
        self._adapters: dict[ProtocolType, ProtocolAdapter] = {}
        self._running = False

        self._bus = MessageBus(self._config)
        self._topics = self._bus.topics

        self._registry = DeviceRegistry(
            max_devices=int(get_conf(
                self._config,
                'gateway.registry.max_devices',
                default=1000
            )),
            stale_timeout=float(get_conf(
                self._config,
                'gateway.registry.timeout_stale',
                default=30.0 * 4
            ))
        )

        self._pipeline = self._build_pipeline()
        self._storage = self._link_storage()
        self._storage_subscriber = StorageSubscriber(self._storage)

        self._reg_adapters()

    @property
    def is_running(self) -> bool:
        """Работает ли шлюз."""
        return self._running

    def _link_storage(self) -> StorageBase:
        """Подключить корректное хранилище на основе env."""
        prefix = get_conf(
            self._config,
            'gateway.general.storage_type',
            default='sqlite'
        )
        if prefix == 'postgresql' or prefix == 'postgres':
            username = get_conf(
                self._config,
                'storage.postgresql.user.username',
                'admin'
            )
            password = get_conf(
                self._config,
                'storage.postgresql.user.password',
                'password'
            )
            host = get_conf(
                self._config,
                'storage.postgresql.address.host',
                'localhost'
            )
            port = int(get_conf(
                self._config,
                'storage.postgresql.address.port',
                5432
            ))
            dbname = get_conf(
                self._config,
                'storage.postgresql.dbname',
                'iotgateway'
            )
            app_name = get_conf(
                self._config,
                'storage.postgresql.app_name',
                'gateway'
            )
            return PostgresStorage(
                connstr=f'postgresql://{username}:{password}'
                        f'@{host}:{port}/{dbname}'
                        f'?application_name={app_name}'
            )
        if prefix == 'sqlite' or prefix == 'aiosqlite':
            return SQLiteStorage(
                db_path=get_conf(
                    self._config,
                    'storage.sqlite.dbpath',
                    ''
                )
            )
        return SQLiteStorage(
            db_path=get_conf(
                self._config,
                'storage.sqlite.dbpath',
                ''
            )
        )

    def _reg_adapters(self) -> None:
        """Регистрирует все переданные адаптеры."""
        adapter_types: dict[str, type[ProtocolAdapter]] = {
            'HTTP': HTTPAdapter,
            'CoAP': CoAPAdapter,
            'WebSocket': WebSocketAdapter,
            'MQTT': MQTTAdapter
        }
        for name, builder in adapter_types.items():
            if get_conf(
                self._config,
                f'adapters.{name.lower()}.enabled',
                False
            ):
                self.register_adapter(builder(self._config))
            else:
                logger.info(f'Adapter {name} disabled in config')

    def _build_pipeline(self) -> Pipeline:
        """Построить конвейер обработки сообщений."""
        pipeline = Pipeline()

        # тут будет добавление этапов конвейера
        pipeline.add_stage(ValidationStage())
        pipeline.add_stage(AuthorizationStage(self._registry))
        pipeline.add_stage(CleanupStage())

        return pipeline

    async def _handle_telemetry(self, message: Message) -> None:
        """Обработать сообщения телеметрии."""
        result = await self._pipeline.execute(message)
        if result:
            await self._registry.heartbeat(result.device_id)
            result.processed = True
            await self._bus.publish(
                self._topics.get(
                    TopicKey.PROCESSED_TELEMETRY,
                    device_id=result.device_id
                ),
                result
            )
        else:
            await self._bus.publish(
                self._topics.get(
                    TopicKey.REJECTED_TELEMETRY,
                    device_id=message.device_id
                ),
                message
            )

    async def _handle_device_status(self, message: Message) -> None:
        """Обработать технические сообщения."""
        if message.message_type == MessageType.STATUS:
            status = DeviceStatus(
                message.payload.get("device_status", "online")
            )
            await self._registry.update_status(message.device_id, status)
        else:
            raise ValueError(
                f'Incorrect message type {message.message_type}'
                f' for status topic {message.message_topic}'
            )

    async def _handle_device_register(self, message: Message) -> None:
        """Обработать сообщение регистрации."""
        if message.message_type == MessageType.REGISTRATION:
            device = Device.from_dict(message.payload)
            device.device_status = DeviceStatus.ONLINE
            await self._registry.register(device)
        else:
            raise ValueError(
                f'Incorrect message type {message.message_type}'
                f' for register topic {message.message_topic}'
            )

    async def _handle_device_heartbeat(self, message: Message) -> None:
        """Обработать сообщение регистрации."""
        if message.message_type == MessageType.HEARTBEAT:
            await self._registry.heartbeat(message.device_id)
        else:
            raise ValueError(
                f'Incorrect message type {message.message_type}'
                f' for heartbeat topic {message.message_topic}'
            )

    def register_adapter(self, adapter: ProtocolAdapter) -> None:
        """Зарегистрировать адаптер протокола."""
        ad_type = adapter.protocol_type
        ad_name = adapter.protocol_name
        if ad_type in self._adapters:
            raise ValueError(f"Adapter '{ad_name}' already registered")

        adapter.set_gateway_context(
            message_bus=self._bus,
            registry=self._registry,
        )
        self._adapters[ad_type] = adapter
        logger.debug("Protocol adapter registered: %s", ad_name)

    async def _start(self) -> None:
        """Запуск шлюза."""
        logger.info('Starting gateway')
        try:
            await self._storage.setup()
        except Exception as exc:
            logger.exception(
                "Failed to connect to storage: %s", exc
            )
        await self._bus.start()

        self._bus.subscribe(
            self._topics.get_subscription_pattern(
                TopicKey.DEVICES_HEARTBEAT
            ),
            self._handle_device_heartbeat
        )
        self._bus.subscribe(
            self._topics.get_subscription_pattern(
                TopicKey.DEVICES_REGISTER
            ),
            self._handle_device_register
        )
        self._bus.subscribe(
            self._topics.get_subscription_pattern(
                TopicKey.DEVICES_STATUS
            ),
            self._handle_device_status
        )
        self._bus.subscribe(
            self._topics.get_subscription_pattern(
                TopicKey.DEVICES_TELEMETRY
            ),
            self._handle_telemetry
        )
        self._bus.subscribe(
            self._topics.get_subscription_pattern(
                TopicKey.PROCESSED_TELEMETRY
            ),
            self._storage_subscriber.handle
        )

        await self._pipeline.setup()

        await self._registry.start_monitor(
            check_interval=float(get_conf(
                self._config,
                'gateway.registry.check_interval',
                30.0
            ))
        )

        for name, adapter in self._adapters.items():
            try:
                await adapter.start()
                logger.debug("Adapter '%s' started", name.value)
            except Exception as exc:
                logger.error(
                    "Failed to start adapter '%s': %s",
                    name,
                    exc,
                    exc_info=True
                )

        self._running = True
        logger.info(
            "Gateway started. Adapters: %s",
            # list(self._adapters.keys())
            [t.value for t in self._adapters.keys()]
        )

    async def _stop(self) -> None:
        """Остановка шлюза."""
        logger.info("Stoping gateway")
        self._running = False

        for name, adapter in reversed(list(self._adapters.items())):
            try:
                await adapter.stop()
                logger.debug("Adapter '%s' stopped", name.value)
            except Exception as exc:
                logger.error(
                    "Error stopping adapter '%s': %s",
                    name, exc, exc_info=True
                )

        try:
            await self._registry.stop_monitor()
        except Exception as exc:
            logger.exception(
                'Error during registry stop: %s',
                exc
            )

        try:
            await self._pipeline.teardown()
        except Exception as exc:
            logger.exception(
                'Error during pipeline teardown: %s',
                exc
            )

        try:
            await self._bus.stop()
        except Exception as exc:
            logger.exception(
                'Error during bus stop: %s',
                exc
            )
        try:
            await self._storage.teardown()
        except Exception as exc:
            logger.exception(
                'Error during storage teardown: %s',
                exc
            )

        logger.info("Gateway stopped")

    async def run_forever(self) -> None:
        """Основной цикл работы шлюза с остановкой по сигналу."""
        await self._start()

        stop_event = asyncio.Event()

        def signal_handler():
            logger.info("Received shutdown signal")
            stop_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, signal_handler)
            except NotImplementedError:
                pass

        try:
            await stop_event.wait()
        except KeyboardInterrupt:
            pass
        finally:
            await self._stop()

    @property
    def status(self) -> dict[str, Any]:
        """Статус работы шлюза."""
        return {
            "gateway": {
                "id": get_conf(
                    self._config,
                    'gateway.general.id',
                    1
                ),
                "name": get_conf(
                    self._config,
                    'gateway.general.name',
                    1
                ),
                "running": self._running,
            },
            "devices": {
                "total": self._registry.count,
                "online": self._registry.online_count,
            },
            "message_bus": self._bus.stats,
            "pipeline": self._pipeline.stats,
            "adapters": {
                name: {"running": adapter.is_running}
                for name, adapter in self._adapters.items()
            },
        }
