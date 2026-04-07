"""Настройка окружения и конфигурации программы."""
from typenv import Env
import logging


env = Env(upper=True)
logger = logging.getLogger(__name__)
SEV_DICT = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}
LOG_DEFAULT = logging.INFO


def get_log_severity() -> str | int:
    """Получить уровень логирования из окружения."""
    debug = env.bool('DEBUG', default=False)
    if debug:
        # return logging.DEBUG
        return 0
    level = str(env.str('LOG_SEVERITY', default=str(LOG_DEFAULT))).upper()
    if level.isalpha():
        level_num = SEV_DICT.get(level, LOG_DEFAULT)
        return level_num
    if level.isnumeric():
        return int(level)
    return LOG_DEFAULT


def load_env(env_path: str = '.env') -> None:
    """Загрузить переменные окружения из указанного файла."""
    try:
        loaded = env.read_env(env_path)
        logger.debug('Loading .env from %s', env_path)
        if not loaded:
            logger.info(
                'Environment variables from %s not loaded, using defaults',
                env_path
            )
    except Exception as ex:
        logger.exception('Couldn\'t load env from %s: %s', env_path, ex)
