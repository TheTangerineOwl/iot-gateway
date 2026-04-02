from dotenv import load_dotenv
from os import getenv
import logging


logger = logging.getLogger(__name__)
SEV_DICT = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}
LOG_DEFAULT = logging.INFO


def get_log_severity():
    debug = getenv('DEBUG', 'False') == 'True'
    if debug:
        return logging.DEBUG
    level = str(getenv('LOG_SEVERITY', LOG_DEFAULT)).upper()
    if level.isalpha():
        level_num = SEV_DICT.get(level, LOG_DEFAULT)
        return level_num
    if level.isnumeric():
        return int(level)
    return LOG_DEFAULT


def load_env(env_path: str):
    try:
        loaded = load_dotenv(env_path)
        logger.debug('Loading .env from %s', env_path)
        if not loaded:
            logger.info(
                'Environment variables from  not loaded, using defaults'
            )
    except Exception as ex:
        logger.exception('Couldn\'t load .env: %s', ex)
