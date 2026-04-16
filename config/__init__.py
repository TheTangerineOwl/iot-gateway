"""Модуль для настройки окружения и конфигурации программы."""
from .config import SEV_DICT, LOG_DEFAULT, get_log_severity_env, load_env

__all__ = ['SEV_DICT', 'LOG_DEFAULT', 'get_log_severity_env', 'load_env']
