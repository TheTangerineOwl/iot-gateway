"""Модуль для настройки окружения и конфигурации программы."""
from pathlib import Path
from .config import (
    SEV_DICT,
    LOG_DEFAULT,
    load_env,
    load_configuration,
    YAMLConfigLoader
)


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'
CONFIG_PATH = BASE_DIR / 'config' / 'configuration'


__all__ = [
    'SEV_DICT', 'LOG_DEFAULT', 'load_env',
    'load_configuration',
    'YAMLConfigLoader',
    'BASE_DIR', 'ENV_PATH', 'CONFIG_PATH'
]
