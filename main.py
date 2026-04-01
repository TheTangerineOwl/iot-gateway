import asyncio
from datetime import datetime
import logging
from sys import exit, stdout, stderr
from core.gateway import Gateway
from protocols.http_adapter import HTTPAdapter


def register_adapters(gateway: Gateway):
    adapter = HTTPAdapter()
    gateway.register_adapter(adapter)


async def main():
    gateway = Gateway()

    logging.basicConfig(
        filename=f'logs/{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log',
        filemode='w',
        encoding='utf-8',
        format="%(asctime)s │ %(levelname)-7s │ %(name)-30s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO
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
