"""Генератор значений с заданным распределением."""
import math
import random


class ValueGenerator:
    """Генератор значений с заданным распределением."""

    @staticmethod
    def gen_sin(
        t: float,
        period: float = 24 * 60 * 60,
        amp: float = 1.0,
        bias_in: float = 0.0,
        bias_out: float = 0.0,
        noise: bool = True,
        noise_mu: float = 0.0,
        noise_sigma: float = 0.3
    ) -> float:
        """Сгенерировать синусоидальных значений."""
        value = amp * math.sin(2 * math.pi * (t + bias_in) / period) + bias_out
        if noise:
            value += random.gauss(noise_mu, noise_sigma)
        return value

    @staticmethod
    def gen_chance(
        chance: float = 0.1
    ) -> bool:
        """Сгенерировать срабатываение с шансом."""
        return random.random() < chance

    @staticmethod
    def gen_uni(
        lower: float = 0.0,
        upper: float = 1.0,
        amp: float = 1.0,
        bias: float = 0.0,
        noise: bool = True,
        noise_mu: float = 0.0,
        noise_sigma: float = 0.3
    ) -> float:
        """Сгенерировать равномерное распределение."""
        value = amp * random.uniform(lower, upper) + bias
        if noise:
            value += random.gauss(noise_mu, noise_sigma)
        return value
