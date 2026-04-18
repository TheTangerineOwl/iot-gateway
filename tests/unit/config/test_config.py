"""Тесты для YAMLConfigLoader."""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from decimal import Decimal
from typing import Iterable
from config.config import YAMLConfigLoader


BASE_DIR = Path(__file__).resolve().parent


@pytest.fixture
def temp_config_dir():
    """Создать временную папку для конфигурации с тестовыми файлами."""
    with tempfile.TemporaryDirectory(dir=BASE_DIR) as tmpdir:
        config_dir = Path(tmpdir)

        gateway_dir = config_dir / 'gateway'
        gateway_dir.mkdir(parents=True)
        gateway_yml = gateway_dir / "default.yml"

        gateway_yml.touch(666)
        gateway_yml.write_text(
            """
logging:
  level: INFO
  debug: false

general:
  id: test_gateway
  timeout: 30
            """
        )

        http_dir = config_dir / "adapters" / "http"
        http_dir.mkdir(parents=True)

        default_http = http_dir / "default.yaml"
        default_http.touch(666)
        default_http.write_text("""
enabled: true
host: 0.0.0.0
port: 8081
url_root: /api/v1
endpoints:
  telemetry: /ingest
  register: /devices/register
health: /health
timeout_reject: 0.5
""")

        running_http = http_dir / "running.yaml"
        running_http.touch(666)
        running_http.write_text("""
port: 8082
debug: true
""")

        sqlite_dir = config_dir / "storage" / "sqlite"
        sqlite_dir.mkdir(parents=True)

        default_sqlite = sqlite_dir / "default.yaml"
        default_sqlite.touch(666)
        default_sqlite.write_text("""
enabled: true
path: ./data/app.db
timeout: 5
cache_size: 2000
journal_mode: WAL
""")

        yield config_dir


@pytest.fixture
def temp_config_empty_dir():
    """Папка с пустым конфигом."""
    with tempfile.TemporaryDirectory(dir=BASE_DIR) as tmpdir:
        config_dir = Path(tmpdir)

        empty_yml = config_dir / "default.yml"
        empty_yml.touch(666)

        yield config_dir


@pytest.fixture
def mock_env():
    """мок для Env."""
    env = MagicMock()
    env_vars = {}

    def env_str(key, default=None):
        """Имитация env.str."""
        return env_vars.get(key, default)

    def env_int(key, default=None):
        """Имитация env.int."""
        value = env_vars.get(key, default)
        if value == default:
            return default
        return int(value)

    def env_list(key, default=None):
        """Имитация env.list."""
        value = env_vars.get(key, default)
        if value == default:
            return default
        if isinstance(value, Iterable):
            return list(value)
        return default

    def env_bool(key, default=None):
        """Имитация env.bool."""
        value = env_vars.get(key, default)
        if value == default:
            return default
        return str(value).lower() in ['true', 'yes', '1']

    def env_float(key, default=None):
        """Имитация env.float."""
        value = env_vars.get(key, default)
        if value == default:
            return default
        return float(value)

    def env_decimal(key, default=None):
        """Имитация env.decimal."""
        value = env_vars.get(key, default)
        if value == default:
            return default
        return Decimal(value)

    env.int = MagicMock(side_effect=env_int)
    env.str = MagicMock(side_effect=env_str)
    env.float = MagicMock(side_effect=env_float)
    env.list = MagicMock(side_effect=env_list)
    env.bool = MagicMock(side_effect=env_bool)
    env.decimal = MagicMock(side_effect=env_decimal)
    env._env_vars = env_vars

    return env


class TestYAMLConfigLoaderInitialization:
    """Тесты инициализации YAMLConfigLoader."""

    def test_init_with_default_folder(self):
        """Тест инициализации с параметрами по умолчанию."""
        loader = YAMLConfigLoader()
        assert loader.config_folder == Path('configuration')
        assert loader.config == {}

    def test_init_with_custom_folder(self):
        """Тест инициализации со своей папкой."""
        loader = YAMLConfigLoader('custom_config')
        assert loader.config_folder == Path('custom_config')


class TestYAMLConfigLoaderLoading:
    """Тесты загрузки конфигурации."""

    def test_load_nonexistent_folder(self):
        """Загрузка из неизвестной директории выдаст ошибку."""
        loader = YAMLConfigLoader('nonexistent_folder')
        with pytest.raises(FileNotFoundError):
            loader.load()

    def test_load_basic_structure(self, temp_config_dir):
        """Тест загрузки базовой конфигурации."""
        loader = YAMLConfigLoader(str(temp_config_dir))
        config = loader.load()

        # Check root level config
        assert 'gateway' in config
        assert 'logging' in config['gateway']
        assert config['gateway']['logging']['level'] == 'INFO'
        assert config['gateway']['logging']['debug'] is False

        assert 'gateway' in config
        assert config['gateway']['general']['id'] == 'test_gateway'

    def test_load_adapters_config(self, temp_config_dir):
        """Тетс загрузки конфига адаптера."""
        loader = YAMLConfigLoader(str(temp_config_dir))
        config = loader.load()

        assert 'adapters' in config
        assert 'http' in config['adapters']
        assert 'host' in config['adapters']['http']
        assert config['adapters']['http']['host'] == '0.0.0.0'
        assert config['adapters']['http']['port'] == 8082
        assert config['adapters']['http']['debug'] is True

    def test_load_storage_config(self, temp_config_dir):
        """Тест загрузки конфига хранилища."""
        loader = YAMLConfigLoader(str(temp_config_dir))
        config = loader.load()

        assert 'storage' in config
        assert 'sqlite' in config['storage']
        assert 'path' in config['storage']['sqlite']
        assert config['storage']['sqlite']['path'] == './data/app.db'

    def test_load_returns_same_as_config_attribute(self, temp_config_dir):
        """Из load возвращается self.config."""
        loader = YAMLConfigLoader(str(temp_config_dir))
        returned_config = loader.load()

        assert returned_config is not None
        assert returned_config == loader.config


class TestGetAdapterConfig:
    """Тесты конфига адаптера."""

    def test_get_existing_adapter(self, temp_config_dir):
        """Для существующих адаптеров полный конфиг."""
        loader = YAMLConfigLoader(str(temp_config_dir))
        loader.load()

        http_config = loader.get_adapter_config('http')
        assert 'enabled' in http_config
        assert 'port' in http_config
        assert http_config['port'] == 8082

    def test_get_nonexistent_adapter(self, temp_config_dir):
        """Для неизвестного адаптера пустой конфиг."""
        loader = YAMLConfigLoader(str(temp_config_dir))
        loader.load()

        config = loader.get_adapter_config('nonexistent')
        assert config == {}


class TestGetStorageConfig:
    """Тесты для получения конфигурации хранилища."""

    def test_get_existing_storage(self, temp_config_dir):
        """Тест получения известной конфигурации."""
        loader = YAMLConfigLoader(str(temp_config_dir))
        loader.load()

        sqlite_config = loader.get_storage_config('sqlite')
        assert 'enabled' in sqlite_config
        assert 'path' in sqlite_config

    def test_get_nonexistent_storage(self, temp_config_dir):
        """Для неизвестного хранилища пустой конфиг."""
        loader = YAMLConfigLoader(str(temp_config_dir))
        loader.load()

        config = loader.get_storage_config('nonexistent')
        assert config == {}


class TestMergeEnv:
    """Тест для слияния с env.."""

    def test_merge_string_values(self, mock_env):
        """Тест слияния строковых значений."""
        mock_env._env_vars['ADAPTERS__HTTP__HOST'] = '127.0.0.1'

        yaml_config = {
            'adapters': {'http': {'host': '0.0.0.0', 'port': 8080}},
        }

        loader = YAMLConfigLoader()
        loader.config = yaml_config
        result = loader.merge_env(yaml_config, mock_env)
        assert result['adapters']['http']['host'] == '127.0.0.1'
        assert result['adapters']['http']['port'] == 8080  # unchanged

    def test_merge_int_values(self, mock_env):
        """Тест слияния целых чисел."""
        mock_env._env_vars['ADAPTERS__HTTP__PORT'] = '9000'

        yaml_config = {'adapters': {'http': {'port': 8080}}}

        loader = YAMLConfigLoader()
        loader.config = yaml_config
        result = loader.merge_env(yaml_config, mock_env)
        assert result['adapters']['http']['port'] == 9000
        assert isinstance(result['adapters']['http']['port'], int)

    def test_merge_bool_values_true(self, mock_env):
        """Тест слияния булевых значений (true)."""
        mock_env._env_vars['GATEWAY__LOGGING__DEBUG'] = 'true'

        yaml_config = {'gateway': {'logging': {'debug': False}}}

        loader = YAMLConfigLoader()
        loader.config = yaml_config
        result = loader.merge_env(yaml_config, mock_env)
        assert result['gateway']['logging']['debug'] is True

    def test_merge_bool_values_yes(self, mock_env):
        """Тест слияния булевых значений (yes)."""
        mock_env._env_vars['GATEWAY__LOGGING__DEBUG'] = 'yes'

        yaml_config = {'gateway': {'logging': {'debug': False}}}

        loader = YAMLConfigLoader()
        loader.config = yaml_config
        result = loader.merge_env(yaml_config, mock_env)
        assert result['gateway']['logging']['debug'] is True

    def test_merge_bool_false_values(self, mock_env):
        """Тест слияния булевых значений (false)."""
        mock_env._env_vars['GATEWAY__LOGGING__DEBUG'] = 'false'

        yaml_config = {'gateway': {'logging': {'debug': True}}}

        loader = YAMLConfigLoader()
        loader.config = yaml_config
        result = loader.merge_env(yaml_config, mock_env)
        assert result['gateway']['logging']['debug'] is False

    def test_merge_float_values(self, mock_env):
        """Тест слияния чисел с плавающей точкой."""
        mock_env._env_vars['ADAPTERS__HTTP__TIMEOUT'] = '2.5'

        yaml_config = {'adapters': {'http': {'timeout': 1.5}}}

        loader = YAMLConfigLoader()
        loader.config = yaml_config
        result = loader.merge_env(yaml_config, mock_env)
        assert result['adapters']['http']['timeout'] == 2.5
        assert isinstance(result['adapters']['http']['timeout'], float)

    def test_merge_does_not_modify_original(self, mock_env):
        """Тест без переопределения изначальной конфигурации."""
        mock_env._env_vars['ADAPTERS__HTTP__PORT'] = '9000'

        yaml_config = {'adapters': {'http': {'port': 8080}}}
        original_port = yaml_config['adapters']['http']['port']

        loader = YAMLConfigLoader()
        loader.config = yaml_config
        result = loader.merge_env(yaml_config, mock_env)
        assert yaml_config['adapters']['http']['port'] == original_port
        assert result['adapters']['http']['port'] == 9000

    def test_merge_empty_config(self):
        """Тест слияния с пустым конфигом."""
        yaml_config = {}
        env = MagicMock()
        env.str = MagicMock(return_value=None)

        loader = YAMLConfigLoader()
        loader.config = yaml_config
        result = loader.merge_env(yaml_config, env)
        assert result == {}

    def test_merge_deeply_nested(self, mock_env):
        """Тест слияния глубоко вложенных значений."""
        mock_env._env_vars[
            'ADAPTERS__HTTP__ENDPOINTS__TELEMETRY'
        ] = '/v2/ingest'

        yaml_config = {
            'adapters': {
                'http': {
                    'endpoints': {
                        'telemetry': '/ingest',
                        'register': '/devices/register',
                    }
                }
            }
        }

        loader = YAMLConfigLoader()
        loader.config = yaml_config
        result = loader.merge_env(yaml_config, mock_env)
        assert (
            result['adapters']['http']['endpoints']['telemetry']
            == '/v2/ingest'
        )
        assert (
            result['adapters']['http']['endpoints']['register']
            == '/devices/register'
        )

    def test_merge_multiple_values(self, mock_env):
        """Тест слияния нескольких значений одновременно."""
        mock_env._env_vars.update({
            'GATEWAY__LOGGING__LEVEL': 'DEBUG',
            'ADAPTERS__HTTP__PORT': '9000',
            'ADAPTERS__HTTP__HOST': '127.0.0.1',
        })

        yaml_config = {
            'gateway': {'logging': {'level': 'INFO', 'debug': False}},
            'adapters': {'http': {'host': '0.0.0.0', 'port': 8081}},
        }

        loader = YAMLConfigLoader()
        loader.config = yaml_config
        result = loader.merge_env(yaml_config, mock_env)
        assert result['gateway']['logging']['level'] == 'DEBUG'
        assert result['adapters']['http']['port'] == 9000
        assert result['adapters']['http']['host'] == '127.0.0.1'


class TestIntegration:
    """Тесты интеграции."""

    def test_full_integration(self, temp_config_dir, mock_env):
        """Полный тест загрузки и слияния."""
        mock_env._env_vars.update({
            'ADAPTERS__HTTP__PORT': '9090',
            'STORAGE__SQLITE__TIMEOUT': '10',
        })

        loader = YAMLConfigLoader(str(temp_config_dir))
        config = loader.load()
        merged = loader.merge_env(config, mock_env)

        assert merged['adapters']['http']['port'] == 9090
        assert merged['storage']['sqlite']['timeout'] == 10

    def test_adapter_and_storage_access(self, temp_config_dir):
        """Тест специальных методов для апаптеров и хранилища.."""
        loader = YAMLConfigLoader(str(temp_config_dir))
        loader.load()

        http_cfg = loader.get_adapter_config('http')
        sqlite_cfg = loader.get_storage_config('sqlite')

        assert http_cfg['enabled'] is True
        assert sqlite_cfg['enabled'] is True
        assert http_cfg['port'] == 8082
        assert sqlite_cfg['path'] == './data/app.db'


class TestEdgeCases:
    """Тесты для ошибок."""

    def test_empty_yaml_file(self, temp_config_empty_dir):
        """Тест загрузки пустого .yml."""
        empty_file = temp_config_empty_dir / "default.yml"
        empty_file.write_text("")

        loader = YAMLConfigLoader(str(temp_config_empty_dir))
        config = loader.load()
        assert config == {}

    def test_yml_and_yaml_extensions(self, temp_config_dir):
        """И .yaml, и .yml загружаются."""
        loader = YAMLConfigLoader(str(temp_config_dir))
        config = loader.load()

        assert 'gateway' in config
        assert 'logging' in config['gateway']
        assert 'adapters' in config
