"""Симулятор взаимодействия устройств со шлюзом по http."""
import aiohttp
import asyncio
from datetime import datetime
from http import HTTPStatus
import logging
from typing import Any
# from config import get_log_severity
from simulator.base.simulator_base import SimMode, Simulator
from simulator.device import SimulatedDevice
from .client import HTTPGatewayClient


logging.basicConfig(
    filename=f'logs/sim/{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log',
    filemode='w',
    encoding='utf-8',
    format="%(asctime)s │ %(levelname)-7s │ %(name)-30s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    # level=get_log_severity()
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)


class HttpSimulator(Simulator):
    """Симулятор http-взаимодействия между шлюзом и устройствами."""

    def __init__(
        self,
        devices:   list[SimulatedDevice],
        client:    HTTPGatewayClient,
        interval:  float = 2.0,
        mode:      SimMode = SimMode.NORMAL,
        burst_n:   int = 5,
        run_once:  bool = False,
    ) -> None:
        """Симулятор http-взаимодействия со шлюзом."""
        super().__init__(
            devices, client, interval, mode, burst_n, run_once
        )

    @property
    def simulator_name(self):
        """Имя симулятора."""
        return 'HTTP Simulator'

    async def _send_raw(
        self,
        device: SimulatedDevice,
        msg: dict[str, Any],
        broken: bool = False,
    ) -> None:
        """Отправить сообщение."""
        device.sent += 1
        tag = "[BROKEN]" if broken else "[GOOD]"
        try:
            status, body = await self._client.send(msg)
            if status in (
                HTTPStatus.OK,
                HTTPStatus.ACCEPTED,
                HTTPStatus.CREATED
            ):
                device.ok += 1
                logger.info(
                    "%-36s (%s) %s payload=%s",
                    device.device_id,
                    device.device.name,
                    tag,
                    msg["payload"],
                )
            else:
                device.failed += 1
                logger.warning(
                    "%-36s (%s) HTTP %d %s body=%s",
                    device.device_id,
                    device.device.name,
                    status,
                    tag,
                    body,
                )
        except aiohttp.ClientConnectorError as exc:
            device.failed += 1
            logger.exception(
                "%-36s (%s) connection refused: %s",
                device.device_id,
                device.device.name,
                exc
            )
        except asyncio.TimeoutError as exc:
            device.failed += 1
            logger.exception(
                "%-36s (%s) timeout (%s)",
                device.device_id,
                device.device.name,
                exc
            )
        except Exception as exc:
            device.failed += 1
            logger.exception(
                "%-36s (%s)  %s: %s",
                device.device_id,
                device.device.name,
                type(exc).__name__,
                exc
            )
