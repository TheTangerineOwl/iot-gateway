import asyncio
from datetime import datetime
import logging
from sys import exit, stdout, stderr
from core.gateway import Gateway
from protocols.http_adapter import HTTPAdapter
from utils.logger import setup_logging


def register_adapters(gateway: Gateway):
    adapter = HTTPAdapter()
    gateway.register_adapter(adapter)


async def main():
    gateway = Gateway()

    strio = open(
        f'logs/{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log',
        'w', encoding='utf-8'
    )

    setup_logging(
        level='DEBUG',
        format="%(asctime)s │ %(levelname)-7s │ %(name)-30s │ %(message)s",
        dateformat="%Y-%m-%d %H:%M:%S",
        stream=strio
    )
    register_adapters(gateway)
    await gateway.run_forever()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger = logging.getLogger(__name__)
        logger.info('Exiting program')
        exit(0)
