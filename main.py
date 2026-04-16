"""Точка входа в приложение шлюза."""
import asyncio
from datetime import datetime
import logging
from pathlib import Path
from sys import exit
from typenv import Env
from core.gateway import Gateway
from config.config import load_env, get_log_severity_env, load_configuration


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / '.env'
CONFIG_PATH = BASE_DIR / 'config' / 'configuration'


async def main():
    """
    Запуск приложения работы шлюза.

    Инициализирует шлюз, задает логирование, регистрирует адаптеры
    и запускает бесконечный цикл работы.
    """
    load_env(ENV_PATH)

    logging.basicConfig(
        filename=f'logs/{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log',
        filemode='w',
        encoding='utf-8',
        format="%(asctime)s │ %(levelname)-7s │ %(name)-30s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=get_log_severity_env()
    )
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('aiosqlite').setLevel(logging.WARNING)
    logging.getLogger('coap-server').setLevel(logging.WARNING)

    # env = Env(upper=True)

    # load_configuration(
    #     config_folder=CONFIG_PATH,
    #     env=env
    # )

    gateway = Gateway()
    await gateway.run_forever()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger = logging.getLogger(__name__)
        logger.info('Shutdown')
        exit(0)
