"""
Отдельный модуль для запуска симуляций датчиков.

Запускает симуляцию взаимодействия шлюза с датчиками
по указанным протоколам.
"""
from .data_generator import SensorType, DataGenerator
from .device import SimulatedDevice
from .faults import FaultType, get_faulty
from .value_generator import ValueGenerator


__all__ = [
    'SensorType', 'DataGenerator',
    'SimulatedDevice',
    'FaultType', 'get_faulty',
    'ValueGenerator'
]
