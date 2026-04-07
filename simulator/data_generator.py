"""Генерация значений датчиков."""
from enum import Enum
from typing import Any
from .value_generator import ValueGenerator as ValGen


class SensorType(str, Enum):
    """Типы измерений датчика."""

    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    POWER = "power"
    MOTION = "motion"


class DataGenerator:
    """Генератор значений датчиков."""

    @staticmethod
    def get_generator(type: SensorType):
        """Получить генератор для нужного типа датчика."""
        return _GENERATORS[type]

    @staticmethod
    def _gen_temp(t: float) -> dict[str, Any]:
        """Сгенерировать значение температуры."""
        value = ValGen.gen_sin(
            t,
            amp=6.0,
            bias_out=22.0
        )
        return {
            "temperature_c": round(value, 2),
            "unit": "celsius",
        }

    @staticmethod
    def _gen_humidity(t: float) -> dict[str, Any]:
        """Сгенерировать значение влажности."""
        value = ValGen.gen_sin(
            t,
            period=12 * 60 * 60,
            amp=15.0,
            bias_out=55.0,
            noise_sigma=1.0
        )
        return {
            "humidity_pct": round(value, 1),
        }

    @staticmethod
    def _gen_power_meter(_t: float) -> dict[str, Any]:
        """Сгенерировать значение счетчика."""
        volt_value = ValGen.gen_uni(
            lower=219.5,
            upper=220.5
        )
        cur_value = ValGen.gen_uni(
            lower=0.1,
            upper=5.0
        )
        return {
            "voltage_v":    round(volt_value, 2),
            "current_a":    round(cur_value, 3),
            "power_w":      round(volt_value * cur_value, 2)
        }

    @staticmethod
    def _gen_motion(_t: float) -> dict[str, Any]:
        """Сгенерировать датчик движения."""
        return {
            "motion_detected": ValGen.gen_chance()
        }


_GENERATORS = {
    SensorType.TEMPERATURE: DataGenerator._gen_temp,
    SensorType.HUMIDITY: DataGenerator._gen_humidity,
    SensorType.POWER: DataGenerator._gen_power_meter,
    SensorType.MOTION: DataGenerator._gen_motion
}
