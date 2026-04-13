"""Тесты для модели девайса."""
from time import time, sleep
from models.device import (
    Device, DeviceStatus, DeviceType, ProtocolType
)
from tests.conftest import not_raises


class TestDeviceStatus:
    """Тесты перечисления DeviceStatus."""

    def test_register(self):
        """Определение типа не зависит от регистра."""
        entype = DeviceStatus.ONLINE
        with not_raises(Exception):
            assert DeviceStatus(entype.lower()) == DeviceStatus.ONLINE
            assert DeviceStatus(entype.upper()) == DeviceStatus.ONLINE
            assert DeviceStatus(entype.capitalize()) == DeviceStatus.ONLINE

    def test_missing(self):
        """Если не может определелить тип, задает неизвестный."""
        typestr = 'some_type'
        with not_raises(Exception):
            result = DeviceStatus(typestr)
        assert result == DeviceStatus.UNKNOWN


class TestDeviceType:
    """Тесты перечисления DeviceType."""

    def test_register(self):
        """Определение типа не зависит от регистра."""
        entype = DeviceType.SENSOR
        with not_raises(Exception):
            assert DeviceType(entype.lower()) == DeviceType.SENSOR
            assert DeviceType(entype.upper()) == DeviceType.SENSOR
            assert DeviceType(entype.capitalize()) == DeviceType.SENSOR

    def test_missing(self):
        """Если не может определелить тип, задает неизвестный."""
        typestr = 'some_type'
        with not_raises(Exception):
            result = DeviceType(typestr)
        assert result == DeviceType.UNKNOWN


class TestProtocolType:
    """Тесты перечисления ProtocolType."""

    def test_register(self):
        """Определение типа не зависит от регистра."""
        entype = ProtocolType.HTTP
        with not_raises(Exception):
            assert ProtocolType(entype.lower()) == ProtocolType.HTTP
            assert ProtocolType(entype.upper()) == ProtocolType.HTTP
            assert ProtocolType(entype.capitalize()) == ProtocolType.HTTP

    def test_missing(self):
        """Если не может определелить тип, задает неизвестный."""
        typestr = 'some_type'
        with not_raises(Exception):
            result = ProtocolType(typestr)
        assert result == ProtocolType.UNKNOWN


class TestDevice:
    """Тесты для модели девайса."""

    def test_touch(self, device: Device):
        """Вызов touch обновляет last_response."""
        device.last_response = time()
        last_response = device.last_response
        device.touch()
        assert device.last_response > last_response

    def test_is_stale_default(self, device: Device):
        """При last_response == 0.0 всегда просрочен."""
        device.last_response = 0.0
        assert device.is_stale()

    def test_is_stale_fresh(self, device: Device):
        """Свежий девайс никогда не просрочен."""
        device.touch()
        assert not device.is_stale()

    def test_is_stale_old(self, device: Device):
        """Если девайс долго не отвечал, то просрочен."""
        device.last_response = time() - 999
        assert device.is_stale(timeout=0)

    def test_to_dict(self):
        """Возвращается правильный словарь."""
        time_created = time()
        sleep(0.01)
        time_touched = time()
        device = Device(
            device_id='dev-id-test',
            name='dev-test',
            device_type=DeviceType.SENSOR,
            device_status=DeviceStatus.ONLINE,
            protocol=ProtocolType.HTTP,
            last_response=time_touched,
            created_at=time_created
        )
        dev_dict = device.to_dict()
        assert str(
            dev_dict.get('device_id')
            ) == 'dev-id-test'
        assert str(
            dev_dict.get('name')
            ) == 'dev-test'
        assert DeviceType(
            dev_dict.get('device_type')
            ) == DeviceType.SENSOR
        assert DeviceStatus(
            dev_dict.get('device_status')
            ) == DeviceStatus.ONLINE
        assert ProtocolType(
            dev_dict.get('protocol')
            ) == ProtocolType.HTTP
        assert float(
            dev_dict.get('last_response')
            ) == time_touched
        assert float(
            dev_dict.get('created_at')
            ) == time_created

    def test_from_dict(self):
        """Правильно десериализируется из словаря."""
        time_touched = time()
        sleep(0.01)
        time_created = time()
        dev_dict = {
            "device_id": 'dev-id-test',
            "name": 'dev-test',
            "device_type": DeviceType.SENSOR.value,
            "protocol": ProtocolType.HTTP.value,
            "device_status": DeviceStatus.ONLINE.value,
            "last_response": time_touched,
            "created_at": time_created,
        }
        with not_raises(Exception):
            device = Device.from_dict(dev_dict)
        assert device.device_id == 'dev-id-test'
        assert device.name == 'dev-test'
        assert device.device_type == DeviceType.SENSOR
        assert device.device_status == DeviceStatus.ONLINE
        assert device.protocol == ProtocolType.HTTP
        assert device.last_response == time_touched
        assert device.created_at == time_created

    def test_dict_roundtrip(self):
        """При использовании to_dict + from_dict получится тот же девайс."""
        time_created = time()
        sleep(0.01)
        time_touched = time()
        device = Device(
            device_id='dev-id-test',
            name='dev-test',
            device_type=DeviceType.SENSOR,
            device_status=DeviceStatus.ONLINE,
            protocol=ProtocolType.HTTP,
            last_response=time_touched,
            created_at=time_created
        )
        new_device = Device.from_dict(device.to_dict())
        assert new_device == device

    def test_from_dict_default(self):
        """При передаче пустого словаря from_dict дает дефолты."""
        default_device = Device()
        with not_raises(Exception):
            device = Device.from_dict({})
        # так как задается новый uuid4, они не совпадут
        device.device_id = default_device.device_id
        # не совпадут из-за задержки
        device.created_at = default_device.created_at
        assert device == default_device
