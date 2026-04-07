"""Вход для симуляции."""
import asyncio
import argparse
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
ENV_PATH = BASE_DIR / '.env'

logging.basicConfig(
    filename=f'logs/sim/{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log',
    filemode='w',
    encoding='utf-8',
    format="%(asctime)s │ %(levelname)-7s │ %(name)-30s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)
env = Env(upper=True)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description='Симулятор датчиков для отладки.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        add_help=True,
        allow_abbrev=True
    )
    p.add_argument('--host', default='127.0.0.1', help='Хост шлюза')
    p.add_argument('--port', default=8081, type=int, help='Порт шлюза')
    p.add_argument(
        '--devices',
        default=3,
        type=int,
        help='Количество датчиков'
    )
    p.add_argument(
        '--interval',
        default=2.0,
        type=float,
        help='Интервал отправки, сек'
    )
    p.add_argument(
        '--mode',
        default=SimMode.NORMAL,
        choices=[mode.value for mode in SimMode],
        help=(
            'normal - обычная работа;\n'
            'burst - пачками по N сообщений;\n'
            'duplicate - дублирование сообщений;\n'
            'invalid - половина сообщений битые.\n'
        )
    )
    p.add_argument(
        '--burst-n',
        default=5,
        type=int,
        help='размер пачки для mode=burst'
    )
    p.add_argument(
        '--once',
        action='store_true',
        help='отправить по 1 сообщению и выйти'
    )
    p.add_argument(
        '--debug',
        action='store_true',
        help='логирование DEBUG'
    )

    return p.parse_args()


async def main() -> None:
    """Запустить симуляции."""
    args = _parse_args()
    if args.debug:
        logging.getLogger(__name__).setLevel(logging.DEBUG)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('aiosqlite').setLevel(logging.WARNING)

    load_env(ENV_PATH.as_posix())

    host = args.host
    port = args.port
    mode = SimMode(args.mode)
    interval = args.interval
    burst_n = args.burst_n
    run_once = args.once
    devices = SimulatedDevice.make_devices(args.devices)

    logger.info(f"датчиков: {len(devices)}")
    logger.info(f"интервал: {interval} сек")
    logger.info(f"режим: {mode.value}, burst: {burst_n}, run_once: {run_once}")
    logger.info('Девайсы: ')
    for d in devices:
        logger.info(f"  {d.device_id:<22}  тип: {d.sensor_type.value}")

    loop = asyncio.get_running_loop()

    async with HTTPGatewayClient(host=host, port=port) as client:
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
