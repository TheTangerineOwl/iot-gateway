"""Настройка окружения и конфигурации программы."""
from datetime import datetime
import logging
from pathlib import Path
from shutil import copyfile, SameFileError
from typenv import Env
from typing import Any, Dict, Optional
import yaml


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


def load_env(env_path: str = '.env') -> None:
    """Загрузить переменные окружения из указанного файла."""
    try:
        loaded = env.read_env(env_path)
        logger.info('Loading .env from %s', env_path)
        if not loaded:
            logger.info(
                'Environment variables from %s not loaded, using defaults',
                env_path
            )
    except Exception as ex:
        logger.exception('Couldn\'t load env from %s: %s', env_path, ex)


_LOGGERS_TO_SUPRESS: set[str] = {
    'aiohttp', 'asyncio', 'aiosqlite', 'coap-server'
}


def _supress_loggers(level: int | str):
    """Подавляет вывод логгеров."""
    for lib in _LOGGERS_TO_SUPRESS:
        logging.getLogger(lib).setLevel(level)


def setup_logging(config: Dict[str, Any]) -> None:
    """Настроить логирование на основе конфигурации."""
    logging_config = config.get('gateway', {}).get('logger', {})

    level = str(logging_config.get('level', 'INFO')).upper()
    debug = logging_config.get('debug', False)
    dir = Path(logging_config.get('dir', 'logs/')).resolve()

    if debug:
        level_num = 0
    elif level.isalpha():
        level_num = SEV_DICT.get(level, LOG_DEFAULT)
    elif level.isnumeric():
        level_num = int(level)

    logging.basicConfig(
        filename=f'{dir}/{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log',
        filemode='w',
        encoding='utf-8',
        format="%(asctime)s │ %(levelname)-7s │ %(name)-30s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=level_num
    )
    _supress_loggers(logging.WARNING)


class YAMLConfigLoader:
    """Загрузчик YAML конфигурации."""

    def __init__(self, folder: str = 'configuration'):
        """Инициализировать конфигуратор."""
        self.config_folder = Path(folder)
        self.config: Dict[str, Any] = {}
        self._adapter_configs: Dict[str, Dict[str, Any]] = {}
        self._storage_configs: Dict[str, Dict[str, Any]] = {}

    def _set_nested_dict(
        self,
        dictionary: Dict[str, Any],
        key_path: str,
        value: Any
    ) -> None:
        """Установить значение во вложенный словарь по пути ключей."""
        keys = key_path.split('.')
        current = dictionary

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                logger.warning(
                    f'Cannot set nested value at {key_path}: '
                    f'{key} is not a dictionary'
                )
                return
            current = current[key]

        final_key = keys[-1]
        if final_key in current and isinstance(current[final_key], dict):
            current[final_key].update(value)
        else:
            current[final_key] = value

    @classmethod
    def _merge_configs(
        cls,
        target: Dict[str, Any],
        source: Dict[str, Any]
    ) -> None:
        """Слить конфигурации (обновить целевую)."""
        for k, v in source.items():
            if (
                k in target
                and isinstance(target[k], dict)
                and isinstance(v, dict)
            ):
                YAMLConfigLoader._merge_configs(target[k], v)
            else:
                target[k] = v

    def _categorize_config(
        self,
        key_path: str,
        config: Dict[str, Any]
    ) -> None:
        """Категоризировать конфиг для быстрого доступа."""
        keys = key_path.split('.')

        if len(keys) >= 2 and keys[0] == 'adapters':
            adapter_name = keys[1]
            if adapter_name not in self._adapter_configs:
                self._adapter_configs[adapter_name] = {}
            self._merge_configs(self._adapter_configs[adapter_name], config)

        elif len(keys) >= 2 and keys[0] == 'storage':
            storage_type = keys[1]
            if storage_type not in self._storage_configs:
                self._storage_configs[storage_type] = {}
            self._merge_configs(self._storage_configs[storage_type], config)

    def _load_yaml_file(
        self,
        file_path: Path,
        parent_key: Optional[str] = None
    ) -> None:
        """Загрузить один YAML файл и добавить его в конфигурацию."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f)

                if file_config is None:
                    logger.warning(f'Empty configuration file: {file_path}')
                    return

                if not isinstance(file_config, dict):
                    logger.warning(
                        f'Configuration file {file_path}'
                        ' does not contain a dictionary'
                    )
                    return

                if parent_key:
                    self._set_nested_dict(self.config, parent_key, file_config)
                    self._categorize_config(parent_key, file_config)
                else:
                    self.config.update(file_config)

                logger.debug(f'Loaded configuration from {file_path}')
        except yaml.YAMLError as exc:
            logger.exception(f'Error parsing YAML file {file_path}: {exc}')
            raise
        except IOError as exc:
            logger.exception(f'Error reading file {file_path}: {exc}')
            raise
        except PermissionError as exc:
            logger.exception('Permission error: ', exc)
            raise

    def _copy_config_file(
        self,
        base_file: Path,
        stem: str,
        directory: Path
    ) -> Path | None:
        """Создает копию файла конфигурации."""
        try:
            sfx = base_file.suffixes.copy()
            if '.example' in sfx:
                sfx.remove('.example')
            name = stem + ''.join(sfx)
            new_path = Path(directory) / name
            if new_path == base_file:
                raise SameFileError('file already exists')
            file = copyfile(base_file, new_path)
            return file
        except Exception as exc:
            logger.exception(
                f'Could not create {name}: ',
                exc
            )
            return None

    def _config_default(
        self,
        files: list[Path],
        directory: Path,
        parent_key: Optional[str] = None
    ):
        """Находит файлы конфигурации и загружает их."""
        running: Optional[Path] = None
        default: Optional[Path] = None
        default_base: Optional[Path] = None

        for file_path in files:
            name = file_path.name.lower()
            if name in ['running.yaml', 'running.yml']:
                running = file_path
            elif name in ['default.yaml', 'default.yml']:
                default = file_path
            elif name in ['default.example.yaml', 'default.example.yml']:
                default_base = file_path

        if running:
            try:
                self._load_yaml_file(running, parent_key)
            except Exception as exc:
                logger.exception(exc)
            finally:
                return
        if default:
            logger.debug(
                f'Could not find running config in {directory}, '
                f'creating from default: {default}.'
            )
            created = self._copy_config_file(default, 'running', directory)
            if created:
                try:
                    self._load_yaml_file(created, parent_key)
                except Exception as exc:
                    logger.exception(exc)
            return
        if default_base:
            f'Could not find running or default config in {directory},'
            f' creating from base: {default_base}.'
            created_def = self._copy_config_file(
                default_base,
                'default',
                directory
            )
            if created_def:
                created_run = self._copy_config_file(
                    created_def,
                    'running',
                    directory
                )
                if created_run:
                    try:
                        self._load_yaml_file(created_run, parent_key)
                    except Exception as exc:
                        logger.exception(exc)

    def _scan_directory(
        self,
        directory: Path,
        parent_key: Optional[str] = None
    ) -> None:
        """Рекурсивно сканировать директорию и загружать yaml-файлы."""
        try:
            entries = sorted(directory.iterdir())
        except PermissionError:
            logger.warning(f'Permisson denied when accessing {directory}')
            return

        files = [f for f in entries if f.is_file()]
        dirs = [d for d in entries if d.is_dir()]

        self._config_default(files, directory, parent_key)

        for dir_path in dirs:
            dir_name = dir_path.name
            next_key = f'{parent_key}.{dir_name}' if parent_key else dir_name
            self._scan_directory(dir_path, next_key)

    def load(self) -> dict:
        """Загрузить конфигурацию из файлов."""
        if not self.config_folder.exists():
            raise FileNotFoundError(
                f'Configuration folder not found: {self.config_folder}'
            )

        if not self.config_folder.is_dir():
            raise FileNotFoundError(
                f'Configuration path is not a directory: {self.config_folder}'
            )

        self.config = {}
        self._adapter_configs = {}
        self._storage_configs = {}

        self._scan_directory(self.config_folder)

        logger.info(
            f'Configuration loaded from {self.config_folder}. '
            f'Root keys: {list(self.config.keys())}'
        )

        return self.config

    def get_adapter_config(self, adapter_name: str) -> dict:
        """Получить конфигурацию адаптера."""
        return self._adapter_configs.get(adapter_name, {})

    def get_storage_config(self, storage_type: str) -> dict:
        """Получить конфигурацию хранилища."""
        return self._storage_configs.get(storage_type, {})

    @classmethod
    def _deep_copy(cls, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: cls._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [cls._deep_copy(item) for item in obj]
        else:
            return obj

    @classmethod
    def _parse_env_from_suffix(
        cls,
        env: Env,
        env_var: str,
        expected_types: list[type]
    ) -> Any:
        """Распарсить env var."""
        try:
            logger.debug(f'Parsing {env_var}, types = {expected_types}')

            env_str = env.str(env_var, default=None)
            if not env_str:
                return None

            if int in expected_types:
                value_int = env.int(env_var, default=None)
                if value_int is not None:
                    logger.debug(f'Converted {env_var} to {value_int}')
                    return value_int
            if bool in expected_types:
                if env_str.lower() in ['true', 'yes', '1']:
                    return True
                if env_str.lower() in ['false', 'no', '0']:
                    return False
                value_bool = env.bool(env_var, default=None)
                if value_bool is not None:
                    logger.debug(f'Converted {env_var} to {value_bool}')
                    return value_bool
            if float in expected_types:
                value_float = env.float(env_var, default=None)
                if value_float is not None:
                    logger.debug(f'Converted {env_var} to {value_float}')
                    return value_float

            if list in expected_types:
                env_list = env.list(env_var, default=None)
                if env_list is not None:
                    logger.debug(f'Converted {env_var} to {env_list}')
                    return env_list

            return env_str
        except Exception as exc:
            logger.exception(
                f'Cannot convert {env_var}, '
                f'keeping str: {exc}'
            )
            return env_str

    @classmethod
    def _merge_env_recursive(
        cls,
        config: Dict[str, Any],
        env: Env,
        path: list
    ) -> None:
        """Рекурсивное слияние env в конфиг."""
        for k, v in list(config.items()):
            current_path = path + [k.upper()]
            env_var_name = '__'.join(current_path)

            if isinstance(v, dict):
                YAMLConfigLoader._merge_env_recursive(
                    v,
                    env,
                    current_path
                )
            else:
                try:
                    expected_types: list[type] = [str]
                    if config[k] is not None:
                        expected_types.append(type(config[k]))
                    env_var = YAMLConfigLoader._parse_env_from_suffix(
                        env=env,
                        env_var=env_var_name,
                        expected_types=expected_types
                    )
                    if env_var is None:
                        continue
                    config[k] = env_var

                    logger.debug(
                        'Override config value '
                        f'from env: {env_var_name}={env_var}'
                    )
                except Exception as exc:
                    logger.debug(
                        'Could not read env var '
                        f'{env_var_name}__: {exc}'
                    )

    def merge_env(self, yaml_config: dict, env: Env) -> dict:
        """Переопределить конфигурацию из YAML значениями из env."""
        result = YAMLConfigLoader._deep_copy(yaml_config)
        YAMLConfigLoader._merge_env_recursive(
            result,
            env,
            []
        )

        self.config = result
        self._adapter_configs = self.config.get('adapters', {})
        self._storage_configs = self.config.get('storage', {})

        return result


def load_configuration(
    config_folder: str = 'configuration',
    env: Optional[Env] = None,
) -> YAMLConfigLoader:
    """
    Загрузить полную конфигурацию из YAML и переменных окружения.

    Это основная функция для загрузки конфигурации. Она:
    1. Загружает YAML конфигурацию из папки
    2. Переопределяет значения переменными окружения (если env задан)
    3. Настраивает логирование
    """
    logger.setLevel(logging.DEBUG)

    loader = YAMLConfigLoader(config_folder)

    loader.config_folder = Path(config_folder)

    config = loader.load()

    if env is not None:
        config = loader.merge_env(config, env)

    setup_logging(config)

    return loader


def _get_conf_rec(keys: list[str], cdict: Dict[str, Any] | None):
    if cdict is None:
        return None
    if len(keys) == 0:
        return cdict
    nest = cdict.get(keys[0])
    return _get_conf_rec(keys[1:], nest)


def get_conf(
    conf: YAMLConfigLoader,
    key: str,
    default: Any | None = None
):
    """Получить значение по комбинации ключей."""
    keys = key.lower().split('.')
    value = _get_conf_rec(keys, conf.config)
    if value is None:
        return default
    return value
