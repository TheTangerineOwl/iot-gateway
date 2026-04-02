"""Модуль адаптеров для протоколов взаимодействия с устройствами."""
from .adapter import ProtocolAdapter
from .http_adapter import HTTPAdapter

__all__ = ['ProtocolAdapter', 'HTTPAdapter']
