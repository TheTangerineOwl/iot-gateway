"""Модуль стандартных топиков сообщений."""
from enum import Enum
import logging
import re
from typing import Any, Optional
from config.config import YAMLConfigLoader


logger = logging.getLogger(__name__)


class TopicKey(str, Enum):
    """Ключи для стандартных топиков."""

    BASE_DEVICES = 'devices'
    BASE_GATEWAY = 'gateway'
    BASE_SYSTEM = 'system'

    DEVICES_TELEMETRY = 'devices.telemetry'
    DEVICES_REGISTER = 'devices.register'
    DEVICES_STATUS = 'devices.status.base'
    DEVICES_STATUS_ONLINE = 'devices.status.online'
    DEVICES_STATUS_OFFLINE = 'devices.status.offline'
    DEVICES_COMMAND = 'devices.command'
    DEVICES_COMMAND_RESPONSE = 'devices.command_response'
    DEVICES_HEARTBEAT = 'devices.heartbeat'

    PROCESSED_TELEMETRY = 'gateway.pipeline.processed.telemetry'
    REJECTED_TELEMETRY = 'gateway.pipeline.rejected.telemetry'

    SYSTEM_HEALTH = 'system.health'
    SYSTEM_METRICS = 'system.metrics'
    SYSTEM_ALERTS = 'system.alerts'


class TopicManager:
    """Класс для получения стандартных топиков."""

    def __init__(self, config: YAMLConfigLoader):
        """Класс для получения стандартных топиков сообщений."""
        self._config = config
        self._topics: dict[str, str] = {}
        self._load_topics()

    def _validate_topic(self, topic: str) -> bool:
        """Валидировать формат топика."""
        pattern = r'^[a-zA-Z0-9_/#/+{}-]+(/[$a-zA-Z0-9_/#/+{}-]+)*$'
        return bool(re.match(pattern, topic))

    def _flatten(
        self,
        nested: dict[str, Any],
        prefix: str = ''
    ):
        """Преобразовать вложенную структуру в плоский словарь."""
        for k, v in nested.items():
            new_key = f'{prefix}.{k}' if prefix else k
            if isinstance(v, dict):
                self._flatten(v, new_key)
            else:
                topic = str(v)
                if self._validate_topic(topic):
                    self._topics[new_key] = topic
                else:
                    logger.info(f"Invalid topic '{v}'")

    def _load_topics(self) -> None:
        """Загрузить топик-конфигурацию."""
        topics = self._config.config.get('topic', {})
        self._flatten(topics, prefix='')

    def get(
        self,
        topic_key: str,
        default: Optional[str] = None,
        **kwargs: str
    ) -> str:
        """Получить топик с подстановкой параметров."""
        topic_template = self._topics.get(topic_key, default)

        if not topic_template:
            raise ValueError(f'Topic {topic_key} not found in configuration')

        if kwargs:
            for param, val in kwargs.items():
                topic_template = topic_template.replace(
                    f'{{{param}}}',
                    str(val)
                )
        return topic_template

    def get_wc(
        self,
        topic_key: str,
        default: Optional[str] = None,
        **kwargs: str
    ) -> str:
        """Получить wildcard-версию топика."""
        topic_template = self.get(topic_key, default, **kwargs)
        return re.sub(r'\{[^}]+\}', '+', topic_template)

    @staticmethod
    def matches(topic: str, pattern: str) -> bool:
        """Проверить соответствие топика паттерну."""
        escape = re.escape(pattern)
        regex_pattern = escape.replace(r'\+', r'[^/]+').replace(r'\#', r'.*')
        regex_pattern = f'^{regex_pattern}$'
        return re.fullmatch(regex_pattern, topic) is not None

    def get_subscription_pattern(self, topic_key: str) -> str:
        """Получить паттерн для подписки на все сообщения типа."""
        return self.get_wc(topic_key)
