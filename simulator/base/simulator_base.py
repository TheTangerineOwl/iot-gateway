"""Абстрактные сущности для симуляторов."""
from abc import ABC, abstractmethod
import asyncio
from enum import Enum
import logging
from random import random
from typing import Any
from simulator.base.client_base import GatewayClient
from simulator.device import SimulatedDevice


logger = logging.getLogger(__name__)


class SimMode(str, Enum):
    """Режим работы симулятора."""

    NORMAL = "normal"  # обычная работа
    BURST = "burst"  # пачки по N сообщений подряд
    DUPLICATE = "duplicate"  # повторная отправка того же message_id
    INVALID = "invalid"  # намеренно сломанные сообщения


class Simulator(ABC):
    """Абстрактный класс симулятора взаимодействия датчиков со шлюзом."""

    def __init__(
        self,
        devices: list[SimulatedDevice],
        client: GatewayClient,
        interval: float = 2.0,
        mode: SimMode = SimMode.NORMAL,
        burst_n: int = 5,
        run_once: bool = False
    ) -> None:
        """Симулятор взаимодействия датчиков со шлюзом."""
        self._devices = devices
        self._client = client
        self._interval = interval
        self._mode = mode
        self._burst_n = burst_n
        self._run_once = run_once
        self._stop = asyncio.Event()

        self._last_messages: dict[str, dict] = {}

    @property
    @abstractmethod
    def simulator_name(self):
        """Название симулятора."""
        return 'simulator'

    def stop(self) -> None:
        """Дать команду остановки симуляции."""
        self._stop.set()

    @abstractmethod
    async def _send_raw(
        self,
        device: SimulatedDevice,
        msg: dict[str, Any],
        broken: bool = False
    ) -> None:
        """Отправить сообщение."""
        pass

    # @abstractmethod
    async def _send_one(
        self, device: SimulatedDevice, broken: bool = False
    ) -> None:
        """Построить и отправить сообщение."""
        msg = device.build_message(broken=broken)
        await self._send_raw(device, msg, broken)

    async def _tick(self, device: SimulatedDevice) -> None:
        """Один шаг работы симулятора."""
        # flake8 ругается на новый match
        # match self._mode:
        #     case SimMode.NORMAL:
        #         await self._send_one(device)

        #     case SimMode.BURST:
        #         for _ in range(self._burst_n):
        #             await self._send_one(device)
        #             await asyncio.sleep(0.01)

        #     case SimMode.DUPLICATE:
        #         msg = device.build_message()
        #         self._last_messages[device.device_id] = msg
        #         # сначала оригинал, потом дубликат
        #         await self._send_raw(device, msg)
        #         await asyncio.sleep(0.05)
        #         await self._send_raw(device, msg)

        #     case SimMode.INVALID:
        #         broken = random() < 0.5
        #         await self._send_one(device, broken=broken)
        # if self._mode == SimMode.NORMAL:
        #     await self._send_one(device)
        if self._mode == SimMode.BURST:
            for _ in range(self._burst_n):
                await self._send_one(device)
                await asyncio.sleep(0.01)
        elif self._mode == SimMode.DUPLICATE:
            msg = device.build_message()
            self._last_messages[device.device_id] = msg
            await self._send_raw(device, msg)
            await asyncio.sleep(0.05)
            await self._send_raw(device, msg)
        elif self._mode == SimMode.INVALID:
            broken = random() < 0.5
            await self._send_one(device, broken=broken)
        else:  # NORMAL
            await self._send_one(device)

    async def _device_loop(self, device: SimulatedDevice) -> None:
        """Цикл работы симулятора."""
        logger.info(
            "%s (%s) started in '%s' simulator",
            device.device_id,
            device.sensor_type.value,
            self.simulator_name)
        try:
            while not self._stop.is_set():
                await self._tick(device)
                if self._run_once:
                    self._stop.set()
                    break
                await asyncio.sleep(self._interval)
        except asyncio.CancelledError:
            pass

    def print_stats(self) -> None:
        """Вывод статистики работы симулятора."""
        total_sent = sum(d.sent for d in self._devices)
        total_ok = sum(d.ok for d in self._devices)
        total_failed = sum(d.failed for d in self._devices)
        logger.info(f"ИТОГ ДЛЯ {self.simulator_name}")
        logger.info(
            f"\t{'устройство':<22} {'отправлено':>10} "
            f"{'ок':>6} {'ошибок':>8}"
        )
        for d in self._devices:
            logger.info(
                f"\t{d.device_id:<22} {d.sent:>10} {d.ok:>6} {d.failed:>8}"
            )
        logger.info(
            f"\t{'ВСЕГО':<22} {total_sent:>10} "
            f"{total_ok:>6} {total_failed:>8}"
        )

    async def run(self) -> None:
        """Симулировать генерацию сообщений и взаимодействие со шлюзом."""
        tasks = [
            asyncio.create_task(self._device_loop(dev), name=dev.device_id)
            for dev in self._devices
        ]

        await self._stop.wait()

        for t in tasks:
            t.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)
        self.print_stats()
