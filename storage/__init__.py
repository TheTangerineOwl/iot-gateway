"""Модуль для хранилищ."""
from .base import StorageBase
from .sqlite import SQLiteStorage

__all__ = ['StorageBase', 'SQLiteStorage']
