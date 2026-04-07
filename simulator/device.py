"""Симуляция девайса."""
from dataclasses import dataclass, field
from time import time
from typing import Any
# from uuid import uuid4
from models.device import Device, DeviceType, DeviceStatus, ProtocolType
from .data_generator import SensorType, DataGenerator
from .faults import get_faulty


@dataclass
class SimulatedDevice:
    """Симулированный девайс."""

    device: Device
    # device_id: str
    sensor_type: SensorType
    sent: int = field(default=0, init=False)
    ok: int = field(default=0, init=False)
    failed: int = field(default=0, init=False)

    @property
    def device_id(self) -> str:
        """Идентификатор девайса."""
        return self.device.device_id

    @classmethod
    def make_devices(cls, n: int) -> list["SimulatedDevice"]:
        """Создать N датчиков случайных типов с детерминированными ID."""
        types = list(SensorType)
        devices = []
        for i in range(n):
            sensor_type = types[i % len(types)]
            device_name = f'{sensor_type.value}-{i + 1:03d}'
            device = Device(
                name=device_name,
                device_type=DeviceType.SENSOR,
                device_status=DeviceStatus.ONLINE,
                protocol=ProtocolType.HTTP
            )
            devices.append(SimulatedDevice(
                device=device,
                sensor_type=sensor_type
            ))
        return devices

    def build_message(self, broken: bool = False) -> dict[str, Any]:
        """Построить сообщение с датчика."""
        t = time()
        payload_gen = DataGenerator.get_generator(self.sensor_type)
        payload = payload_gen(t)

        if broken:
            payload = get_faulty(payload)

        return {
            "device_id":  self.device_id,
            'name': self.device.name,
            'device_type': self.device.device_type,
            'protocol': self.device.protocol,
            'device_status': self.device.device_status,
            # "message_id": str(uuid4()),
            # "timestamp":  t,
            "payload":    payload,
        }

    def build_register(self):
        """Построить сообщение для регистрации девайса."""
        # t = time()
        return {
            "device_id":  self.device_id,
            'name': self.device.name,
            'device_type': self.device.device_type,
            'protocol': self.device.protocol,
            'device_status': self.device.device_status,
            # "message_id": str(uuid4()),
            # "timestamp":  t,
            'payload': {}
        }
