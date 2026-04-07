"""Симуляция девайса."""
from dataclasses import dataclass, field
from time import time
from typing import Any
from uuid import uuid4
from .data_generator import SensorType, DataGenerator
from .faults import get_faulty


@dataclass
class SimulatedDevice:
    """Симулированный девайс."""

    device_id: str
    device_type: SensorType
    sent: int = field(default=0, init=False)
    ok: int = field(default=0, init=False)
    failed: int = field(default=0, init=False)

    @classmethod
    def make_devices(cls, n: int) -> list["SimulatedDevice"]:
        """Создать N датчиков случайных типов с детерминированными ID."""
        types = list(SensorType)
        devices = []
        for i in range(n):
            sensor_type = types[i % len(types)]
            device_id = f"{sensor_type.value}-{i + 1:03d}"
            devices.append(SimulatedDevice(
                device_id=device_id, device_type=sensor_type
            ))
        return devices

    def build_message(self, broken: bool = False) -> dict[str, Any]:
        """Построить сообщение с датчика."""
        t = time()
        payload_gen = DataGenerator.get_generator(self.device_type)
        payload = payload_gen(t)

        if broken:
            payload = get_faulty(payload)

        return {
            "device_id":  self.device_id,
            "message_id": str(uuid4()),
            "timestamp":  t,
            "payload":    payload,
        }

    def build_register(self):
        """Построить сообщение для регистрации девайса."""
        t = time()
        return {
            'device_id': self.device_id,
            'message_id': str(uuid4()),
            'timestamp': t,
            'payload': {}
        }
