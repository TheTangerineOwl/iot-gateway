# Адаптеры протоколов

Каждый адаптер наследуется от `ProtocolAdapter` (`protocols/adapters/base.py`), реализует методы `start()`, `stop()` и `send_command()`, подключается к шине сообщений (`MessageBus`) и реестру устройств (`DeviceRegistry`) через `set_gateway_context()`.

Включение/отключение адаптера — переменная `ADAPTERS__<NAME>__ENABLED=True/False`.

---

## HTTP

**Порт по умолчанию:** `8081`  
**Библиотека:** `aiohttp`

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/api/v1/ingest` | Приём телеметрии |
| `POST` | `/api/v1/devices/register` | Регистрация устройства |
| `GET` | `/api/v1/health` | Статус адаптера |
| `GET` | `/api/v1/devices/{device_id}/commands` | Polling команд устройством |

Телеметрия публикуется на шину, адаптер ожидает (таймаут `timeout_reject`) возможного отклонения конвейером — если отклонено, возвращает `422 Unprocessable Entity`.

**Примеры:**

```bash
# Регистрация
curl -X POST http://localhost:8081/api/v1/devices/register \
  -H "Content-Type: application/json" \
  -d '{"device_id": "sensor-01", "device_name": "Temp Sensor", "device_type": "temperature"}'

# Телеметрия
curl -X POST http://localhost:8081/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"device_id": "sensor-01", "timestamp": "2026-01-01T00:00:00Z", "data": {"temperature": 22.5}}'

# Health check
curl http://localhost:8081/api/v1/health
```

**Конфигурация (YAML):**

```yaml
# config/configuration/adapters/http/default.yaml
enabled: true
host: 0.0.0.0
port: 8081
url_root: /api/v1
endpoints:
  telemetry: /ingest
  register: /devices/register
  health: /health
timeout_reject: 0.5      # сек — время ожидания отклонения конвейером
command_timeout: 5.0     # сек — таймаут доставки команды устройству
```

**.env:**

```env
ADAPTERS__HTTP__ENABLED=True
ADAPTERS__HTTP__HOST=0.0.0.0
ADAPTERS__HTTP__PORT=8081
ADAPTERS__HTTP__URL_ROOT=/api/v1
ADAPTERS__HTTP__ENDPOINTS__TELEMETRY=/ingest
ADAPTERS__HTTP__ENDPOINTS__REGISTER=/devices/register
ADAPTERS__HTTP__ENDPOINTS__HEALTH=/health
ADAPTERS__HTTP__TIMEOUT_REJECT=0.5
```

---

## WebSocket

**Порт по умолчанию:** `8082`  
**Библиотека:** `aiohttp`

| Метод | Путь | Описание |
|---|---|---|
| `WS GET` | `/api/v1/ws/ingest` | Двунаправленный WebSocket-канал |
| `POST` | `/api/v1/ws/devices/register` | HTTP-регистрация устройства |
| `GET` | `/api/v1/ws/health` | Статус адаптера |

Устройство устанавливает постоянное WebSocket-соединение. Тип сообщения определяется полем `type` в JSON (`telemetry`, `register`, `command_response`). Адаптер хранит маппинг `device_id → WebSocketResponse` для отправки команд.

**Пример (JavaScript):**

```javascript
const ws = new WebSocket('ws://localhost:8082/api/v1/ws/ingest');

ws.onopen = () => {
  // Регистрация
  ws.send(JSON.stringify({
    type: 'register',
    device_id: 'sensor-02',
    device_name: 'Humidity Sensor',
    device_type: 'humidity'
  }));
  // Телеметрия
  ws.send(JSON.stringify({
    type: 'telemetry',
    device_id: 'sensor-02',
    data: { humidity: 56.8 }
  }));
};
```

**Конфигурация (YAML):**

```yaml
# config/configuration/adapters/websocket/default.yaml
enabled: true
host: 0.0.0.0
port: 8082
url_root: /api/v1/ws
endpoints:
  general: /ingest
  register_http: /devices/register
  health_http: /health
heartbeat: 30.0    # сек — интервал ping/pong
timeout_reject: 0.5
```

**.env:**

```env
ADAPTERS__WEBSOCKET__ENABLED=True
ADAPTERS__WEBSOCKET__HOST=0.0.0.0
ADAPTERS__WEBSOCKET__PORT=8082
ADAPTERS__WEBSOCKET__URL_ROOT=/api/v1/ws
ADAPTERS__WEBSOCKET__HEARTBEAT=30.0
ADAPTERS__WEBSOCKET__TIMEOUT_REJECT=0.5
```

---

## CoAP

**Порт по умолчанию:** `5683` (UDP)  
**Библиотека:** `aiocoap`

| Метод | Ресурс | Описание |
|---|---|---|
| `POST` | `/api/v1/coap/ingest` | Приём телеметрии |
| `POST` | `/api/v1/coap/devices/register` | Регистрация устройства |
| `GET` | `/api/v1/coap/health` | Статус адаптера |

Работает по UDP. Ответные коды: `2.04 Changed` — принято, `4.03 Forbidden` — отклонено конвейером, `4.00 Bad Request` — ошибка разбора.

**Примеры (coap-client):**

```bash
# Регистрация
echo -n '{"device_id":"sensor-03","device_name":"Motion","device_type":"motion"}' | \
  coap-client -m post -t application/json coap://localhost/api/v1/coap/devices/register

# Телеметрия
echo -n '{"device_id":"sensor-03","data":{"motion":true}}' | \
  coap-client -m post -t application/json coap://localhost/api/v1/coap/ingest
```

**Конфигурация (YAML):**

```yaml
# config/configuration/adapters/coap/default.yaml
enabled: true
host: 127.0.0.1
port: 5683
url_root: /api/v1/coap
endpoints:
  telemetry: /ingest
  register: /devices/register
  health: /health
timeout_reject: 0.5
```

**.env:**

```env
ADAPTERS__COAP__ENABLED=True
ADAPTERS__COAP__HOST=127.0.0.1
ADAPTERS__COAP__PORT=5683
ADAPTERS__COAP__URL_ROOT=/api/v1/coap
ADAPTERS__COAP__TIMEOUT_REJECT=0.5
```

---

## MQTT

**Порт брокера по умолчанию:** `1883`  
**Библиотека:** `aiomqtt`  
**Протоколы:** MQTT 3.1.1 (`version: 4`) и MQTT 5.0 (`version: 5`)

Адаптер подключается к внешнему MQTT-брокеру (например, Mosquitto) и подписывается на топики. Для локальной разработки можно запустить брокер через `scripts/mqtt_broker.sh`.

**Подписки (входящие):**

| Топик | Описание |
|---|---|
| `devices/+/telemetry` | Телеметрия с устройств |
| `devices/+/register` | Регистрация устройства |
| `devices/+/status` | Обновление статуса |
| `devices/+/command/response` | Ответ устройства на команду |

**Публикации (исходящие):**

| Топик | Описание |
|---|---|
| `devices/{device_id}/command` | Отправка команды устройству |

**Примеры (mosquitto_pub / mosquitto_sub):**

```bash
# Регистрация
mosquitto_pub -h localhost -p 1883 -t devices/sensor-04/register \
  -m '{"device_id":"sensor-04","device_name":"Pressure","device_type":"pressure"}'

# Телеметрия
mosquitto_pub -h localhost -p 1883 -t devices/sensor-04/telemetry \
  -m '{"device_id":"sensor-04","data":{"pressure":1013.25}}'

# Подписка для проверки
mosquitto_sub -h localhost -p 1883 -t 'devices/#'
```

**Конфигурация (YAML):**

```yaml
# config/configuration/adapters/mqtt/default.yaml
enabled: true
client_id: iot-gateway
broker:
  host: 127.0.0.1
  port: 1883
bind:
  address: 0.0.0.0
  port: 0
auth:
  username: ''
  password: ''
tls:
  use: false
  insecure: false
  ca_certs: ''
  certfile: ''
  keyfile: ''
  keyfile_password: ''
version: '4'            # '4' = MQTT 3.1.1, '5' = MQTT 5.0
keepalive: 60
qos: 1
clean_session: true
reconnect_delay: 5      # сек — начальный интервал переподключения
max_reconnect_delay: 300
timeout_reject: 2.0
subscriptions:
  telemetry:
    topic: 'devices/+/telemetry'
    qos: 1
  register:
    topic: 'devices/+/register'
    qos: 1
  status:
    topic: 'devices/+/status'
    qos: 1
  command_response:
    topic: 'devices/+/command/response'
    qos: 1
```

**.env:**

```env
ADAPTERS__MQTT__ENABLED=True
ADAPTERS__MQTT__CLIENT_ID=iot-gateway
ADAPTERS__MQTT__BROKER__HOST=127.0.0.1
ADAPTERS__MQTT__BROKER__PORT=1883
ADAPTERS__MQTT__AUTH__USERNAME=
ADAPTERS__MQTT__AUTH__PASSWORD=
ADAPTERS__MQTT__TLS__USE=False
ADAPTERS__MQTT__VERSION='4'
ADAPTERS__MQTT__KEEPALIVE=60
ADAPTERS__MQTT__QOS=1
ADAPTERS__MQTT__RECONNECT_DELAY=5
ADAPTERS__MQTT__MAX_RECONNECT_DELAY=300
ADAPTERS__MQTT__SUBSCRIPTIONS__TELEMETRY__TOPIC='devices/+/telemetry'
ADAPTERS__MQTT__SUBSCRIPTIONS__TELEMETRY__QOS=1
```

---

## Management

**Порт по умолчанию:** `8001`  
**Библиотека:** `aiohttp`

Внутренний HTTP-адаптер для мониторинга и управления шлюзом. Используется веб-приложением. Не принимает телеметрию.

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/management/status` | Статус шлюза (адаптеры, реестр, pipeline) |
| `GET` | `/management/config` | Конфигурация шлюза |
| `GET` | `/management/devices/` | Список устройств из реестра |
| `GET` | `/management/devices/{device_id}` | Данные конкретного устройства |
| `POST` | `/management/devices/{device_id}/command` | Отправка команды устройству |

**Тело команды:**

```json
{
  "command": "reboot",
  "params": { "delay": 5 },
  "timeout": 10.0
}
```

**Конфигурация (YAML):**

```yaml
# config/configuration/adapters/management/default.yaml
enabled: true
host: 0.0.0.0
port: 8001
url_root: /management
endpoints:
  status: /status
  config: /config
```

**.env:**

```env
ADAPTERS__MANAGEMENT__ENABLED=True
ADAPTERS__MANAGEMENT__HOST=0.0.0.0
ADAPTERS__MANAGEMENT__PORT=8001
```

---

## Добавление нового адаптера

1. Создать файл `protocols/adapters/your_adapter.py`
2. Наследоваться от `ProtocolAdapter` и реализовать `start()`, `stop()`, `send_command()`, `protocol_type`
3. Добавить конфигурацию в `config/configuration/adapters/your_adapter/default.example.yaml`
4. Зарегистрировать адаптер в `core/gateway.py`
