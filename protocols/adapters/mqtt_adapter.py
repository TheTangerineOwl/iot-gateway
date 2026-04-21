"""
Адаптер для протокола MQTT.

Топики:
    - devices/{device_id}/telemetry  - телеметрия с устройств
    - devices/{device_id}/register   - регистрация устройств
    - devices/{device_id}/status     - обновление статуса устройств
    - devices/{device_id}/command/response - ответы на команды
    - devices/{device_id}/command    - команды (публикуются с шлюза)
"""
import asyncio
import json
import logging
from typing import Optional, Dict, Any
from contextlib import AsyncExitStack
from aiomqtt import Client, MqttError, TLSParameters, ProtocolVersion
import ssl
from config.config import YAMLConfigLoader
from config.topics import TopicKey
from protocols.adapters.base import ProtocolAdapter
from models.message import Message, MessageType
from models.device import ProtocolType


logger = logging.getLogger(__name__)


class MQTTAdapter(ProtocolAdapter):
    """MQTT адаптер протокола."""

    def __init__(self, config: YAMLConfigLoader) -> None:
        """Инициализация MQTT протокола."""
        super().__init__(config)
        self._adapter_config = self._config.get_adapter_config(
            self.protocol_name
        )
        self.broker_host = self._adapter_config.get(
            'broker', {}
        ).get('host', '0.0.0.0')
        self.broker_port = int(self._adapter_config.get(
            'broker', {}
        ).get('port', 1883))
        self.bind_address = self._adapter_config.get(
            'bind', {}
        ).get('address', '0.0.0.0')
        self.bind_port = int(self._adapter_config.get(
            'bind', {}
        ).get('port', 1883))

        self.username = self._adapter_config.get(
            'auth', {}
        ).get('username', '')
        self.password = self._adapter_config.get(
            'auth', {}
        ).get('password', '')
        self.client_id = self._adapter_config.get('client_id', 'iot-gateway')
        self.clean_session: bool = self._adapter_config.get(
            'clean_session', True
        ) is True
        self.keepalive = int(self._adapter_config.get('keepalive', 60))
        self.qos = int(self._adapter_config.get('qos', 1))

        self.use_tls = self._adapter_config.get(
            'tls', {}
        ).get('use', False) is True
        self.tls_ca_certs = self._adapter_config.get(
            'tls', {}
        ).get('ca_certs', '')
        self.tls_certfile = self._adapter_config.get(
            'tls', {}
        ).get('certfile', '')
        self.tls_keyfile = self._adapter_config.get(
            'tls', {}
        ).get('keyfile', '')
        self._tls_keyfile_password = self._adapter_config.get(
            'tls', {}
        ).get('keyfile_password', '')
        self.tls_insecure = self._adapter_config.get(
            'tls', {}
        ).get('insecure', False) is True
        # MQTT protocol version (4 for 3.1.1, 5 for 5.0)
        env_prot_version = self._adapter_config.get('version', '4')
        if env_prot_version.startswith('5'):
            self.protocol_version = ProtocolVersion.V5
        else:
            self.protocol_version = ProtocolVersion.V311

        self.client: Optional[Client] = None
        self.is_connected = False

        self._default_reconnect_interval: float = self._adapter_config.get(
            'reconnect_delay', 3
        )
        self._reconnect_interval = self._default_reconnect_interval
        self._max_reconnect_interval: float = self._adapter_config.get(
            'max_reconnect_delay', 300
        )
        self._exit_stack: Optional[AsyncExitStack] = None

        self._message_task: Optional[asyncio.Task] = None
        self._run_task: Optional[asyncio.Task] = None

        logger.info(
            f"MQTT Adapter initialized: "
            f"{self.broker_host}:{self.broker_port} "
            f"(protocol v{self.protocol_version}, QoS={self.qos})"
        )

    @property
    def protocol_type(self):
        """Тип протокола."""
        return ProtocolType.MQTT

    async def start(self) -> None:
        """Запустить MQTT адаптер."""
        self._running = True
        logger.info('Starting MQTT adapter')
        self._run_task = asyncio.create_task(self.run())

    async def stop(self) -> None:
        """Остановить MQTT адаптер."""
        self._running = False
        logger.info('Stopping MQTT adapter')
        await self.disconnect()

    async def connect(self) -> bool:
        """Подключиться к MQTT брокеру."""
        try:
            # Для менеджера контекста
            self._exit_stack = AsyncExitStack()
            await self._exit_stack.__aenter__()

            tls_params = None

            if self.use_tls:
                tls_ciphers = None

                tls_params = TLSParameters(
                    ca_certs=self.tls_ca_certs,
                    certfile=self.tls_certfile,
                    keyfile=self.tls_keyfile,
                    keyfile_password=self._tls_keyfile_password,
                    cert_reqs=ssl.CERT_NONE
                    if self.tls_insecure
                    else ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLS,
                    ciphers=tls_ciphers
                )
                logger.info("TLS/SSL enabled for MQTT connection")

            client_kwargs: dict[str, Any] = {
                "hostname": self.broker_host,
                "port": self.broker_port,
                "identifier": self.client_id,
                "keepalive": self.keepalive,
                "clean_session": self.clean_session,
                "protocol": self.protocol_version,
                "username": self.username,
                "password": self.password,
                "tls_params": tls_params,
                "bind_address": self.bind_address,
                "bind_port": self.bind_port
            }

            if not self.client:
                self.client = Client(**client_kwargs)
                logger.info(
                    f"MQTT adapter initialized "
                    f"({self.broker_host}:{self.broker_port})"
                )

            await self._exit_stack.enter_async_context(self.client)

            self.is_connected = True
            self._reconnect_interval = self._default_reconnect_interval
            logger.info("Successfully connected to MQTT broker")

            await self._subscribe_topics()
            return True

        except MqttError as e:
            logger.exception(f"MQTT connection error: {e}")
            self.is_connected = False
            await self._cleanup()
            return False
        except Exception as e:
            logger.exception(f"Unexpected error during MQTT connection: {e}")
            self.is_connected = False
            await self._cleanup()
            return False

    async def disconnect(self) -> bool:
        """Отключиться от MQTT брокера."""
        try:
            logger.info("Disconnecting from MQTT broker")
            await self._cleanup()
            logger.info("Successfully disconnected from MQTT broker")
            return True
        except Exception as e:
            logger.exception(f"Error during MQTT disconnect: {e}")
            return False

    async def _cleanup(self) -> None:
        """Очистить MQTT подключение и задачи."""
        if self._message_task and not self._message_task.done():
            self._message_task.cancel()
            try:
                await self._message_task
            except asyncio.CancelledError:
                pass
            self._message_task = None

        if self._exit_stack:
            await self._exit_stack.__aexit__(None, None, None)
            self._exit_stack = None

        self.client = None
        self.is_connected = False

    async def send_message(
        self,
        device_id: str,
        topic: str,
        message: Dict[str, Any]
    ) -> bool:
        """Отправить сообщение на девайс через MQTT."""
        if not self.is_connected or not self.client:
            logger.warning(
                f"Cannot send command to {device_id}: not connected to broker"
            )
            return False

        try:
            payload = json.dumps(message)

            await self.client.publish(
                topic=topic,
                payload=payload,
                qos=self.qos,
                retain=False
            )

            logger.debug(f"Command published to {device_id}")
            return True

        except MqttError as e:
            logger.exception(
                f"MQTT error publishing command to {device_id}: {e}"
            )
            return False
        except Exception as e:
            logger.exception(f"Error sending command to {device_id}: {e}")
            return False

    async def send_command(
        self,
        device_id: str,
        command: Dict[str, Any]
    ) -> bool:
        """Отправить команду на девайс через MQTT топик."""
        if not self.is_connected or not self.client:
            logger.warning(
                f"Cannot send command to {device_id}: not connected to broker"
            )
            return False

        try:
            if self._topics is None:
                raise RuntimeError('Topic manager is not set')
            topic = self._topics.get(
                TopicKey.DEVICES_COMMAND,
                device_id=device_id
            )
            payload = json.dumps(command)

            await self.client.publish(
                topic=topic,
                payload=payload,
                qos=self.qos,
                retain=False
            )

            logger.debug(f"Command published to {device_id}")
            return True

        except MqttError as e:
            logger.exception(
                f"MQTT error publishing command to {device_id}: {e}"
            )
            return False
        except Exception as e:
            logger.exception(f"Error sending command to {device_id}: {e}")
            return False

    async def _subscribe_topics(self) -> None:
        """Подписаться на топики и запустить получатель сообщений."""
        if not self.client or not self.is_connected:
            logger.warning("Cannot subscribe: client not initialized")
            return

        try:

            subscriptions = self._adapter_config.get(
                'topics', {}
            ).get('subscriptions', {})

            for k, v in subscriptions.items():
                topic = v.get('topic')
                qos = int(v.get('qos', 1))
                await self.client.subscribe(topic, qos=qos)
                logger.info(
                    f'Subscribed to MQTT topic for {k}: {topic} (QoS={qos})'
                )

            self._message_task = asyncio.create_task(self._receive_messages())

        except MqttError as e:
            logger.exception(f"Error subscribing to topics: {e}")
            self.is_connected = False

    async def _receive_messages(self) -> None:
        """Получать и обрабатывать сообщения с MQTT брокера."""
        if not self.client:
            logger.warning("Cannot receive messages: client not initialized")
            return

        try:
            async for message in self.client.messages:
                try:
                    await self._process_mqtt_message(message)
                except Exception as e:
                    logger.exception(f"Error processing MQTT message: {e}")

        except asyncio.CancelledError:
            logger.debug("Message receiver task cancelled")
        except MqttError as e:
            logger.exception(f"MQTT error receiving messages: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error in message receiver: {e}")

    async def _process_mqtt_message(self, mqtt_message: Any) -> None:
        """Обработать входящие MQTT сообщения и опубликовать на шине."""
        try:
            topic = mqtt_message.topic.value
            payload_bytes = mqtt_message.payload

            # devices/{device_id}/{category}
            parts = topic.split("/")
            if len(parts) < 3 or parts[0] != "devices":
                logger.warning(f"Invalid topic format: {topic}")
                return

            device_id = parts[1]
            message_category = "/".join(parts[2:])

            try:
                if isinstance(payload_bytes, bytes):
                    payload_str = payload_bytes.decode("utf-8")
                else:
                    payload_str = str(payload_bytes)

                payload = json.loads(
                    payload_str
                ) if payload_str.strip() else {}
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON payload: {payload_str[:100]}")
                payload = {"raw": payload_str}

            message_type, message_topic = self._parse_message_type(
                message_category,
                device_id=device_id
            )

            message = Message(
                device_id=device_id,
                message_type=message_type,
                payload=payload,
                protocol=ProtocolType.MQTT,
                message_topic=message_topic
            )

            logger.debug(
                f"Received {message_type.value} from {device_id} "
                f"(topic: {topic})"
            )

            if self._bus is None:
                raise RuntimeError('MQTT adapter not connected to bus')
            await self._bus.publish(message.message_topic, message)

        except Exception as e:
            logger.exception(f"Error processing MQTT message: {e}")

    def _parse_message_type(
        self,
        message_category: str,
        **kwargs: str
    ) -> tuple[MessageType, str]:
        """Преобразовать топик MQTT в топик MessageBus."""
        mapping = {
            "telemetry": (
                MessageType.TELEMETRY,
                self.get_topic(TopicKey.DEVICES_TELEMETRY, **kwargs)
            ),
            "register": (
                MessageType.REGISTRATION,
                self.get_topic(TopicKey.DEVICES_REGISTER, **kwargs)
            ),
            "status": (
                MessageType.STATUS,
                self.get_topic(TopicKey.DEVICES_STATUS, **kwargs)
            ),
            "command/response": (
                MessageType.COMMAND_RESPONSE,
                self.get_topic(TopicKey.DEVICES_COMMAND_RESPONSE, **kwargs)
            ),
        }
        return mapping.get(
            message_category,
            mapping.get('telemetry', (MessageType.UNKNOWN, ''))
        )

    async def run(self) -> None:
        """Главный цикл работы адаптера."""
        logger.info("Starting MQTT adapter main loop")

        try:
            while self._running:
                try:
                    if not self.is_connected:
                        if await self.connect():
                            await asyncio.sleep(10)
                        else:
                            wait_time = self._reconnect_interval
                            logger.info(
                                "Retrying MQTT connection in %s seconds",
                                wait_time
                            )
                            await asyncio.sleep(wait_time)
                            self._reconnect_interval = min(
                                self._reconnect_interval * 1.5,
                                self._max_reconnect_interval
                            )
                    else:
                        await asyncio.sleep(10)

                except asyncio.CancelledError:
                    logger.info("MQTT adapter run loop cancelled")
                    await self.disconnect()
                    break
                except Exception as e:
                    logger.exception(f"Error in MQTT adapter main loop: {e}")
                    self.is_connected = False
                    await self._cleanup()

        except asyncio.CancelledError:
            logger.info("MQTT adapter shutting down")
            await self.disconnect()
        finally:
            self._running = False

    async def health_check(self) -> Dict[str, Any]:
        """Вернуть статус адаптера."""
        return {
            "adapter": self.protocol_name,
            "connected": self.is_connected,
            "broker": f"{self.broker_host}:{self.broker_port}",
            "client_id": self.client_id,
            "protocol_version": f"MQTT {self.protocol_version}",
            "qos": self.qos,
            "tls_enabled": self.use_tls,
            "keepalive": self.keepalive,
        }
