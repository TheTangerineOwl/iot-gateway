# Конфигурация

Конфигурация строится из двух источников: **иерархических YAML-файлов** и **переменных окружения** (`.env`). Переменные окружения имеют приоритет над YAML и переопределяют соответствующие параметры.

---

## Структура YAML-конфигурации

Файлы конфигурации расположены в `config/configuration/` и организованы иерархически — каждая директория соответствует разделу конфига:

```
config/configuration/
├── adapters/
│   ├── http/
│   │   └── default.yaml          # конфиг HTTP-адаптера
│   ├── websocket/
│   │   └── default.yaml
│   ├── coap/
│   │   └── default.yaml
│   ├── mqtt/
│   │   └── default.yaml
│   └── management/
│       └── default.yaml
├── gateway/
│   └── default.yaml              # основные параметры шлюза
├── storage/
│   ├── sqlite/
│   │   └── default.yaml
│   └── postgresql/
│       └── default.yaml
└── topic/
    └── default.yaml              # топики шины сообщений
```

`YAMLConfigLoader` (`config/config.py`) рекурсивно обходит папку, формируя единый конфиг-словарь. Имя директории становится ключом верхнего уровня (`adapters`, `storage`, `topic` и т.д.), а вложенные директории образуют вложенные ключи.

### Приоритет файлов

При загрузке в каждой директории ищутся файлы в следующем порядке приоритета:

| Файл | Описание |
|---|---|
| `running.yaml` | **Активная конфигурация** — используется в первую очередь |
| `default.yaml` | Конфигурация по умолчанию |
| `default.example.yaml` | Шаблон — копируется в `default.yaml` при первом запуске |

> Скрипт `scripts/delete_configs.sh` удаляет `default.yaml` и `running.yaml`, оставляя только `.example`-файлы, что позволяет сбросить конфигурацию к шаблонам.

### Пример YAML-файлов

**`config/configuration/gateway/default.yaml`:**
```yaml
general:
  id: '1'
  name: IoT Gateway
  allowed_hosts: ['localhost', '127.0.0.1']
  storage_type: sqlite
registry:
  max_devices: 1000
  timeout_stale: 120.0
  check_interval: 30.0
message_bus:
  max_queue: 1000
  timeout: 1.0
logger:
  dir: logs/
  debug: false
  level: INFO
```

**`config/configuration/adapters/http/default.yaml`:**
```yaml
enabled: true
host: 0.0.0.0
port: 8081
url_root: /api/v1
endpoints:
  telemetry: /ingest
  register: /devices/register
  health: /health
timeout_reject: 0.5
```

**`config/configuration/storage/sqlite/default.yaml`:**
```yaml
dbpath: data/telemetry.db
```

**`config/configuration/topic/default.yaml`:**
```yaml
devices:
  telemetry: 'devices/{device_id}/telemetry'
  register: 'devices/{device_id}/register'
  command: 'devices/{device_id}/command'
  command_response: 'devices/{device_id}/command/response'
  status:
    base: 'devices/{device_id}/status'
    online: 'devices/{device_id}/status/online'
    offline: 'devices/{device_id}/status/offline'
gateway:
  pipeline:
    processed:
      telemetry: 'gateway/processed/telemetry/{device_id}'
    rejected:
      telemetry: 'gateway/rejected/telemetry/{device_id}'
```

---

## Переменные окружения (.env)

Переменные окружения полностью отражают структуру YAML: вложенность передаётся через `__` (двойное подчёркивание), разделы верхнего уровня — это первый сегмент имени переменной.

**Синтаксис:** `РАЗДЕЛ__ПОДРАЗДЕЛ__ПАРАМЕТР=значение`

> Переменные читаются из `.env` (локально) или `.env.docker` (Docker). Для начала работы скопировать: `cp .env.example .env`

### Шлюз (`GATEWAY__*`)

```env
GATEWAY__GENERAL__ID=1
GATEWAY__GENERAL__NAME='IoT Gateway'
GATEWAY__GENERAL__ALLOWED_HOSTS=127.0.0.1,localhost
GATEWAY__GENERAL__STORAGE_TYPE=sqlite        # sqlite | postgresql

GATEWAY__REGISTRY__MAX_DEVICES=1000
GATEWAY__REGISTRY__TIMEOUT_STALE=120.0       # сек — устройство считается неактивным
GATEWAY__REGISTRY__CHECK_INTERVAL=30.0       # сек — интервал проверки устаревших устройств

GATEWAY__MESSAGE_BUS__MAX_QUEUE=1000
GATEWAY__MESSAGE_BUS__TIMEOUT=1.0

GATEWAY__LOGGER__DIR=logs/
GATEWAY__LOGGER__LEVEL=INFO                  # DEBUG | INFO | WARNING | ERROR | CRITICAL
GATEWAY__LOGGER__DEBUG=False                 # True — логировать всё (уровень 0)
```

### Топики (`TOPIC__*`)

```env
TOPIC__DEVICES__TELEMETRY='devices/{device_id}/telemetry'
TOPIC__DEVICES__REGISTER='devices/{device_id}/register'
TOPIC__DEVICES__COMMAND='devices/{device_id}/command'
TOPIC__DEVICES__COMMAND_RESPONSE='devices/{device_id}/command/response'
TOPIC__DEVICES__STATUS__BASE='devices/{device_id}/status'
TOPIC__DEVICES__STATUS__ONLINE='devices/{device_id}/status/online'
TOPIC__DEVICES__STATUS__OFFLINE='devices/{device_id}/status/offline'
TOPIC__GATEWAY__PIPELINE__PROCESSED__TELEMETRY='gateway/processed/telemetry/{device_id}'
TOPIC__GATEWAY__PIPELINE__REJECTED__TELEMETRY='gateway/rejected/telemetry/{device_id}'
```

### Адаптеры (`ADAPTERS__*`)

```env
# HTTP
ADAPTERS__HTTP__ENABLED=True
ADAPTERS__HTTP__HOST=0.0.0.0
ADAPTERS__HTTP__PORT=8081
ADAPTERS__HTTP__URL_ROOT=/api/v1
ADAPTERS__HTTP__ENDPOINTS__TELEMETRY=/ingest
ADAPTERS__HTTP__ENDPOINTS__REGISTER=/devices/register
ADAPTERS__HTTP__ENDPOINTS__HEALTH=/health
ADAPTERS__HTTP__TIMEOUT_REJECT=0.5

# WebSocket
ADAPTERS__WEBSOCKET__ENABLED=True
ADAPTERS__WEBSOCKET__HOST=0.0.0.0
ADAPTERS__WEBSOCKET__PORT=8082
ADAPTERS__WEBSOCKET__URL_ROOT=/api/v1/ws
ADAPTERS__WEBSOCKET__HEARTBEAT=30.0
ADAPTERS__WEBSOCKET__TIMEOUT_REJECT=0.5

# CoAP
ADAPTERS__COAP__ENABLED=True
ADAPTERS__COAP__HOST=127.0.0.1
ADAPTERS__COAP__PORT=5683
ADAPTERS__COAP__URL_ROOT=/api/v1/coap
ADAPTERS__COAP__TIMEOUT_REJECT=0.5

# MQTT
ADAPTERS__MQTT__ENABLED=True
ADAPTERS__MQTT__CLIENT_ID=iot-gateway
ADAPTERS__MQTT__BROKER__HOST=127.0.0.1
ADAPTERS__MQTT__BROKER__PORT=1883
ADAPTERS__MQTT__AUTH__USERNAME=
ADAPTERS__MQTT__AUTH__PASSWORD=
ADAPTERS__MQTT__TLS__USE=False
ADAPTERS__MQTT__TLS__INSECURE=False
ADAPTERS__MQTT__TLS__CA_CERTS=
ADAPTERS__MQTT__TLS__CERTFILE=
ADAPTERS__MQTT__TLS__KEYFILE=
ADAPTERS__MQTT__TLS__KEYFILE_PASSWORD=
ADAPTERS__MQTT__VERSION='4'              # '4' = MQTT 3.1.1, '5' = MQTT 5.0
ADAPTERS__MQTT__KEEPALIVE=60
ADAPTERS__MQTT__QOS=1
ADAPTERS__MQTT__CLEAN_SESSION=True
ADAPTERS__MQTT__RECONNECT_DELAY=5
ADAPTERS__MQTT__MAX_RECONNECT_DELAY=300
ADAPTERS__MQTT__TIMEOUT_REJECT=2.0
ADAPTERS__MQTT__SUBSCRIPTIONS__TELEMETRY__TOPIC='devices/+/telemetry'
ADAPTERS__MQTT__SUBSCRIPTIONS__TELEMETRY__QOS=1
ADAPTERS__MQTT__SUBSCRIPTIONS__REGISTER__TOPIC='devices/+/register'
ADAPTERS__MQTT__SUBSCRIPTIONS__REGISTER__QOS=1
ADAPTERS__MQTT__SUBSCRIPTIONS__STATUS__TOPIC='devices/+/status'
ADAPTERS__MQTT__SUBSCRIPTIONS__STATUS__QOS=1
ADAPTERS__MQTT__SUBSCRIPTIONS__COMMAND_RESPONSE__TOPIC='devices/+/command/response'
ADAPTERS__MQTT__SUBSCRIPTIONS__COMMAND_RESPONSE__QOS=1

# Management
ADAPTERS__MANAGEMENT__ENABLED=True
ADAPTERS__MANAGEMENT__HOST=0.0.0.0
ADAPTERS__MANAGEMENT__PORT=8001
```

### Хранилище (`STORAGE__*`)

```env
# SQLite
STORAGE__SQLITE__DBPATH=data/telemetry.db

# PostgreSQL
STORAGE__POSTGRESQL__USER__USERNAME=admin
STORAGE__POSTGRESQL__USER__PASSWORD=password
STORAGE__POSTGRESQL__ADDRESS__HOST=localhost
STORAGE__POSTGRESQL__ADDRESS__PORT=5432
STORAGE__POSTGRESQL__DBNAME=iotgateway
STORAGE__POSTGRESQL__APP_NAME=gateway
```

### Веб-приложение (`WEB__*`)

```env
WEB__HOST=0.0.0.0
WEB__PORT=8090
WEB__SECRET_KEY=changeme-in-prod
WEB__ADMIN_USER=admin
WEB__ADMIN_PASSWORD=changeme
WEB__TOKEN_EXPIRE_MINUTES=60
WEB__LOGS_DIR=logs/
WEB__CHECK_TIMEOUT=5.0
WEB__GATEWAY_MANAGEMENT_URL=http://localhost:8001
```

---

## Публичный whitelist конфигурации

Файл `config/configuration/public_config_whitelist.example.txt` содержит список ключей конфигурации, которые будут отдаваться при запросе `GET /management/config`. Все ключи, не попавшие в whitelist, из ответа исключаются — это позволяет не раскрывать чувствительные данные (пароли, секреты).

---

## Топики шины сообщений

`TopicManager` (`config/topics.py`) загружает топики из раздела `topic` конфига и предоставляет к ним доступ через `TopicKey` (enum). Топики поддерживают подстановку параметров через `{param}`:

```python
topic = manager.get(TopicKey.DEVICES_TELEMETRY, device_id='sensor-01')
```

Wildcard-версия для подписки:

```python
pattern = manager.get_wc(TopicKey.DEVICES_TELEMETRY)
```
