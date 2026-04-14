# IoT-шлюз на Python
IoT-шлюз на Python, предназначенный для запуска на одноплатном устройстве или в Docker-контейнере. Принимает телеметрию от устройств по нескольким протоколам, обрабатывает ее через конвейер этапов обработки и сохраняет в базе данных.
## Возможности
- Множественные протоколы: HTTP, WebSocket, CoAP (UDP)
- Гибкое хранилище: SQLite для разработки, PostgreSQL для production
- Docker-ready: Полная поддержка Docker и docker-compose
- Pipeline обработки: Расширяемая система этапов обработки данных
- Регистрация устройств: Автоматическое управление подключенными устройствами
- Мониторинг: Health-check endpoints для всех адаптеров
- Логирование: Структурированные логи
## Быстрый старт
### Запуск через Docker
#### 1. Клонировать репозиторий
```bash
git clone https://github.com/TheTangerineOwl/iot-gateway.git
cd iot-gateway
```
#### 2. Настроить переменные окружения
Создать файл `.env.docker` для настройки PostgreSQL и портов:
```bash
# отредактировать переменные при необходимости
cp env.example .env.docker
```
#### 3. Запустить контейнеры
```bash
docker-compose up -d
```
Это поднимет:
- PostgreSQL на порту `5432`
- IoT Gateway с адаптерами на портах `8081` (HTTP), `8082` (WebSocket), `5683` (CoAP/UDP)
#### 4. Проверить статус
Проверить логи:
```bash
docker-compose logs -f gateway
```
Проверить health-check:
```bash
curl http://localhost:8081/api/v1/health
curl http://localhost:8082/api/v1/ws/health
```
Просмотреть запущенные контейнеры:
```bash
docker-compose ps
```
#### 5. Остановка
Остановить контейнеры:
```bash
docker-compose down
```
Остановить и удалить данные:
```bash
docker-compose down -v
```
### Локальный запуск
Для разработки или тестирования без Docker:
#### 1. Установить зависимости
```bash
python -m venv venv
# Linux / macOS
source venv/bin/activate
# Windows
venv\Scripts\activate
pip install -r requirements.txt
```
#### 2. Настроить окружение
```bash
cp env.example .env
# Отредактировать .env при необходимости
```
#### 3. Создать директории
```bash
mkdir -p data logs logs/sim
```
#### 4. Запуск
```bash
python main.py
```
#### 5. (Опционально) Запустить симулятор
В отдельной консоли:
```bash
# Просмотр параметров
python run_sim.py --help
# Запуск с параметрами по умолчанию
python run_sim.py
# Запуск с кастомными параметрами
python run_sim.py --devices 5 --interval 10
```
Симулятор создает тестовые устройства, регистрирует их на шлюзе и отправляет телеметрию.
## Конфигурация
### Переменные окружения
Основной файл конфигурации: `env.example` (скопировать в `.env`)
#### Основные настройки
```env
GATEWAY_ID=1
GATEWAY_NAME='IoT Gateway'
# Лимиты устройств
DEVICES_MAX=1000
DEVICES_TIMEOUT_STALE=120.0
DEVICES_CHECK_INTERVAL=30.0
# Очередь сообщений
MESQ_MAX_LEN=10000
MESQ_TIMEOUT=1.0
```
#### Хранилище данных
**SQLite**:
```env
STORAGE_TYPE=sqlite
STORAGE_DB_CONNSTR=data/telemetry.db
```
**PostgreSQL**:
```env
STORAGE_TYPE=postgresql
STORAGE_DB_CONNSTR=postgresql://user:password@host:5432/dbname?application_name=gateway
```
#### HTTP Адаптер
```env
HTTP_HOST=0.0.0.0
HTTP_PORT=8081
HTTP_URL_ROOT=/api/v1
HTTP_URL_TELEMETRY=/ingest
HTTP_URL_REGISTER=/devices/register
HTTP_URL_HEALTH=/health
```
#### WebSocket Адаптер
```env
WS_HOST=0.0.0.0
WS_PORT=8082
WS_URL_ROOT=/api/v1/ws
WS_URL_WS=/ingest
WS_URL_REGISTER=/devices/register
WS_URL_HEALTH=/health
```
#### CoAP Адаптер
```env
COAP_HOST=0.0.0.0
COAP_PORT=5683
COAP_URL_ROOT=/api/v1/coap
COAP_URL_WS=/ingest
COAP_URL_REGISTER=/devices/register
COAP_URL_HEALTH=/health
COAP_TIMEOUT_REJECT=0.5
```
#### Логирование и отладка
```env
DEBUG=True
LOG_SEVERITY=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```
### Docker-специфичные настройки
В `docker-compose.yml` используется файл `.env.docker` для переопределения настроек:
```yaml
environment:
  STORAGE_TYPE: postgresql
  STORAGE_DB_CONNSTR: >-
    postgresql://${POSTGRES_USER:-admin}:${POSTGRES_PASSWORD:-password}
    @postgres:5432/${POSTGRES_DB:-iotgateway}?application_name=gateway
```
## Протоколы и адаптеры
### HTTP Адаптер
**Регистрация устройства:**
```bash
curl -X POST http://localhost:8081/api/v1/devices/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "sensor-001",
    "device_name": "Temperature Sensor",
    "device_type": "temperature"
  }'
```
**Отправка телеметрии:**
```bash
curl -X POST http://localhost:8081/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "sensor-001",
    "timestamp": "2026-04-07T12:00:00Z",
    "data": {
      "temperature": 22.5,
      "humidity": 45.3
    }
  }'
```
**Health check:**
```bash
curl http://localhost:8081/api/v1/health
```
### WebSocket Адаптер
**Подключение:**
```javascript
const ws = new WebSocket('ws://localhost:8082/api/v1/ws/ingest');
// Регистрация
ws.send(JSON.stringify({
  type: 'register',
  device_id: 'sensor-002',
  device_name: 'Humidity Sensor',
  device_type: 'humidity'
}));
// Отправка телеметрии
ws.send(JSON.stringify({
  type: 'telemetry',
  device_id: 'sensor-002',
  timestamp: new Date().toISOString(),
  data: {
    humidity: 56.8,
    temperature: 23.1
  }
}));
```
### CoAP Адаптер (UDP)
CoAP адаптер работает по UDP на порту 5683.
**Регистрация (с использованием coap-client):**
```bash
echo -n '{"device_id":"sensor-003","device_name":"Motion Sensor","device_type":"motion"}' | \
  coap-client -m post -t application/json coap://localhost:5683/api/v1/coap/devices/register
```
**Отправка телеметрии:**
```bash
echo -n '{"device_id":"sensor-003","timestamp":"2026-04-07T12:00:00Z","data":{"motion":true}}' | \
  coap-client -m post -t application/json coap://localhost:5683/api/v1/coap/ingest
```
## Тестирование
### Установка зависимостей для тестирования
```bash
pip install pytest pytest-asyncio pytest-postgresql
```
### Запуск тестов
```bash
# Все тесты
pytest
# Только юнит-тесты
pytest tests/unit/ -m unit
# Только интеграционные тесты
pytest tests/integration -m integration
# Конкретный модуль с подробным выводом
pytest tests/unit/test_registry.py -v
```
### Тесты в Docker
```bash
# Запустить тесты в контейнере
docker-compose run --rm gateway pytest
# Интерактивная отладка
docker-compose run --rm gateway bash
# > pytest tests/unit/test_registry.py -v
```
## Логирование
Логи генерируются в logs/ с названием в формате ГГГГ-ММ-ДД_чч-мм-сс при каждом запуске шлюза.
### Формат логов
```
%(asctime)s │ %(levelname)-7s │ %(name)-30s │ %(message)s
```
Пример:
```
2026-04-07 12:00:00 │ INFO    │ core.gateway                   │ Starting gateway
2026-04-07 12:00:01 │ INFO    │ protocols.http_adapter         │ HTTP adapter listening on 0.0.0.0:8081
2026-04-07 12:00:01 │ INFO    │ protocols.ws_adapter           │ WebSocket adapter listening on 0.0.0.0:8082
2026-04-07 12:00:01 │ INFO    │ protocols.coap_adapter         │ CoAP adapter listening on 0.0.0.0:5683
```
### Просмотр логов в Docker
```bash
# Все логи
docker-compose logs -f
# Только gateway
docker-compose logs -f gateway
# Последние 100 строк
docker-compose logs --tail=100 gateway
# С timestamps
docker-compose logs -f -t gateway
```
## Разработка
### Структура проекта
```
iot-gateway/
├── config/                 # Конфигурация
│   ├── __init__.py
│   └── config.py          # Загрузка переменных окружения
├── core/                  # Ядро системы
│   ├── gateway.py         # Основной класс шлюза
│   ├── message_bus.py     # Очередь сообщений
│   ├── registry.py        # Реестр устройств
│   └── pipeline/          # Конвейер обработки
│       ├── base.py        # Базовый класс Stage
│       ├── pipeline.py    # Конвейер обработки
│       └── stages.py      # Встроенные этапы
├── models/                # Модели данных
│   ├── device.py          # Device, DeviceStatus
│   ├── message.py         # Message
│   └── telemetry.py       # Telemetry
├── protocols/             # Адаптеры протоколов
│   ├── adapters/
│   │   ├── http_adapter.py
│   │   ├── ws_adapter.py
│   │   └── coap_adapter.py
│   └── message_builder.py
├── storage/               # Хранилище данных
│   ├── base.py
│   ├── sqlite_storage.py
│   └── postgresql_storage.py
├── Dockerfile
├── docker-compose.yml
├── env.example
├── requirements.txt
└── main.py               # Точка входа
```
### Добавление нового адаптера
1. Создать файл в `protocols/adapters/your_adapter.py`
2. Наследоваться от базового класса адаптера
3. Реализовать методы `start()`, `stop()`, обработку сообщений
4. Зарегистрировать в `protocols/adapters/__init__.py`
5. Добавить конфигурацию в `env.example`
### Добавление нового этапа Pipeline
1. Создать класс в `core/pipeline/stages.py`
2. Наследоваться от `PipelineStage`
3. Реализовать метод `async def process(self, message: Message) -> Message`
4. Зарегистрировать в конфигурации `PIPELINE_STAGES`
### Docker разработка
```bash
# Пересобрать образ после изменений
docker-compose build gateway
# Запустить с пересборкой
docker-compose up -d --build
# Войти в контейнер для отладки
docker-compose exec gateway bash
# Просмотр переменных окружения
docker-compose exec gateway env
```
## :handshake: Вклад в проект
1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменений (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request
## 📄 Лицензия
будет добавлена позже

## Контакты  
---
GitHub: :call_me_hand:[@TheTangerineOwl](https://github.com/TheTangerineOwl)
Project Link: [https://github.com/TheTangerineOwl/iot-gateway](https://github.com/TheTangerineOwl/iot-gateway)
**Последнее обновление**: 14.04.2026
---