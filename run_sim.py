"""Вход для симуляции."""
import asyncio
from datetime import datetime
import logging
from pathlib import Path
import signal
from typenv import Env
from config import load_env
from simulator.device import SimulatedDevice
from simulator.http.client import HTTPGatewayClient
from simulator.http.simulator import SimMode, HttpSimulator


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / '.env.sim'

logging.basicConfig(
    filename=f'logs/sim/{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log',
    filemode='w',
    encoding='utf-8',
    format="%(asctime)s │ %(levelname)-7s │ %(name)-30s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)
env = Env(upper=True)


async def main() -> None:
    """Запустить симуляции."""
    logging.getLogger(__name__).setLevel(logging.DEBUG)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('aiosqlite').setLevel(logging.WARNING)
    load_env(ENV_PATH.as_posix())

    mode = SimMode.INVALID
    interval = 30
    burst_n = 5
    run_once = False
    devices = SimulatedDevice.make_devices(3)

    logger.info(f"датчиков: {len(devices)}")
    logger.info(f"интервал: {interval} сек")
    logger.info(f"режим: {mode.value}, burst: {burst_n}, run_once: {run_once}")
    logger.info('Девайсы: ')
    for d in devices:
        logger.info(f"  {d.device_id:<22}  тип: {d.device_type.value}")

    loop = asyncio.get_running_loop()

    async with HTTPGatewayClient() as client:
        for d in devices:
            await client.register(d)

        sim = HttpSimulator(
            devices=devices,
            client=client,
            interval=interval,
            mode=mode,
            burst_n=burst_n,
            run_once=run_once,
        )
        logger.info('симулятор: %s', sim.simulator_name)

        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, sim.stop)
        except NotImplementedError:
            pass
        try:
            await sim.run()
        finally:
            sim.print_stats()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Http simulator shutdown')
        pass
