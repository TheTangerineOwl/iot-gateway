"""Точка входа в приложение шлюза."""
import asyncio
import logging
from sys import exit, platform
from typenv import Env
from config import CONFIG_PATH, ENV_PATH
from config.config import load_configuration, load_env
from core.gateway import Gateway


async def main():
    """
    Запуск приложения работы шлюза.

    Инициализирует шлюз, задает логирование, регистрирует адаптеры
    и запускает бесконечный цикл работы.
    """
    load_env(ENV_PATH)

    env = Env(upper=True)

    config = load_configuration(
        config_folder=CONFIG_PATH,
        env=env
    )

    gateway = Gateway(config)
    await gateway.run_forever()


if __name__ == '__main__':
    try:
        if platform == 'win32':
            asyncio.set_event_loop_policy(
                asyncio.WindowsSelectorEventLoopPolicy()
            )
        asyncio.run(main())
    except KeyboardInterrupt:
        logger = logging.getLogger(__name__)
        logger.info('Shutdown')
        exit(0)
