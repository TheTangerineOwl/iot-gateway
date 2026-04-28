# IoT-шлюз на Python

IoT-шлюз на Python, предназначенный для запуска на одноплатном устройстве или в Docker-контейнере. Принимает телеметрию от устройств по нескольким протоколам, обрабатывает её через конвейер этапов обработки и сохраняет в базе данных.

## Структура проекта

<details>
<summary>
Структура проекта
</summary>

```
iot-gateway/
├── config/                                         # Модуль конфигурации env + YAML
│   ├── configuration/                              # директория с иерархической YAML-конфигурацией
│   │   ├── adapters/                               # иерархическая конфигурация адаптеров
│   │   │   ├── http/                               # конфигурация HTTP
│   │   │   │   └── default.yaml                    # файл с конфигурацией
│   │   │   └── <другие адаптеры>
│   │   ├── gateway/                                # основная конфигурация ядра
│   │   ├── storage/                                # конфигурация хранилищ
│   │   │   ├── sqlite/                             # конфигурация SQLite
│   │   │   │   └── default.yaml
│   │   │   └── <другие хранилища>
│   │   ├── topic/                                  # конфигурация с топиками (темами) для подписок шины
│   │   │   └── default.yaml
│   │   └── public_config_whitelist.example.txt     # параметры конфигурации, которые будут выведены при запросе /gateway/config
│   ├── config.py                                   # Загрузка переменных окружения
│   └── topics.py                                   # Менеджер топиков для единого их формата
├── core/                                           # Ядро системы
│   ├── gateway.py                                  # Основной класс шлюза
│   ├── message_bus.py                              # Очередь сообщений
│   ├── registry.py                                 # Реестр устройств
│   ├── command_tracker.py                          # Трекер для результатов отправки команд на устройства
│   └── pipeline/                                   # Конвейер обработки
│       ├── base.py                                 # Базовый класс Stage
│       ├── pipeline.py                             # Конвейер обработки
│       └── stages.py                               # Встроенные этапы
├── models/                                         # Модели данных
│   ├── device.py                                   # Устройство и связанные с ним модели
│   ├── message.py                                  # Сообщение и связанные с ним модели
│   └── telemetry.py                                # Запись телеметрии и связанные с ним модели
├── protocols/                                      # Адаптеры протоколов
│   ├── adapters/
│   │   ├── base.py                                 # Базовый класс адаптера
│   │   ├── http_adapter.py                         # HTTP-адаптер
│   │   ├── websocket_adapter.py                    # WebSocket-адаптер
│   │   ├── coap_adapter.py                         # CoAP-адаптер
│   │   ├── mqtt_adapter.py                         # MQTT-адаптер
│   │   └── management_adapter.py                   # Менеджмент-адаптер для доступа веб-приложения через API
│   └── message_builder.py                          # Построение единого формата сообщений в JSON
├── scripts/                                        # Вспомогательные скрипты для работы с программой
│   ├── delete_configs.sh                           # Удаляет из папки config/configuration файлы default.yaml и running.yaml, остаются файлы с суффиксом .example (пересоздание и сброс running.yaml будет доработан)
│   ├── env_from_example.sh                         # Копирует выбранный .env.example в выбранный .env
│   ├── mqtt_broker.sh                              # запускает одиночный контейнер с Mosquitto
│   └── clear_logs.sh                               # Очищает заданную папку с логами 
├── storage/                                        # Хранилище данных
│   ├── base.py                                     # Базовый класс хранилища
│   ├── subscriber.py                               # Подписчик шины сообщений для добавления телеметрии в хранилище
│   ├── sqlite.py                                   # Хранилище SQLite
│   └── postgresql.py                               # Хранилище PostgreSQL
├── tests/                                          # Тесты pytest
├── web/                                            # Веб-приложение
│   ├── backend/                                    # Бэкенд веб-приложения
│   │   ├── dependencies/ 
│   │   ├── models/
│   │   ├── routers/
│   │   ├── schemas/ 
│   │   ├── services/
│   │   └── main.py                                 # Точка запуска веб-приложения
│   ├── frontend/                                   # Фронтенд веб-приложения
│   ├── Dockerfile
│   └── requirements.txt                            # требования веб-приложения
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── pytest.ini
└── main.py                                         # Точка входа
```

</details>

## Возможности

### Конвейер обработки сообщений телеметрии

Сообщения телеметрии проходят через конвейер обработки Pipeline с возможностью настраивать этапы.

### Поддержка основных протоколов IoT

Шлюз поддерживает использование протоколов HTTP, WebSocket, CoAP и MQTT с возможностью легкого добавления новых модулей.

Подробнее - в [protocols/README.md](protocols/README.md).

### Локальное или удаленное хранилище данных

Шлюз поддерживает использование локальной базы SQLite или удаленного хранилища PostgreSQL.

Подробнее - в [storage/README.md](storage/README.md)

### API

Даже при запуске без веб-приложения, если включен management-адаптер, возможны запросы к шлюзу по API.

### Веб-интерфейс

Веб-интерфейс - независимый модуль проекта, предоставляющий возможность мониторинга и управления через браузер.

Подробнее - в [web/README.md](web/README.md).

### Docker

Шлюз поддерживает Docker и `docker-compose.yaml` для развертывания на любых устройствах с поддержкой Docker. Docker производит автоматическую сборку, настройку и запуск всех модулей проекта. Подробнее см. в [Быстрый старт](#быстрый-старт)

### Гибкая конфигурация с помощью YAML и .env

Все основные аспекты программы - хосты, порты, логирование, БД, включение и отключение адаптеров - может быть произведено через файлы в формате YAML и переменные окружения, причем переменные окружения переопределяют соответствующие переменные YAML.

Подробнее - в [config/README.md](config/README.md).

## Быстрый старт

### Локальный запуск

**Windows**:
```bash
git clone https://github.com/TheTangerineOwl/iot-gateway.git
cd iot-gateway
python -m venv venv && . venv\\Scripts\\activate
pip install -r requirements.txt
pip install -r web/requirements.txt  # если планируется использование web-приложения
cp .env.example .env  # отредактировать переменные при необходимости
mkdir -p data logs
python main.py
```

**Linux**:
```bash
git clone https://github.com/TheTangerineOwl/iot-gateway.git
cd iot-gateway
python3 -m venv venv && source venv/bin/activate
pip install -r web/requirements.txt  # если планируется использование web-приложения
cp .env.example .env  # отредактировать переменные при необходимости
mkdir -p data logs
python3 main.py
```

### Запуск веб-приложения

Подробнее о запуске веб-приложения - в [web/README.md](web/README.md)

### Docker

`docker-compose.yaml` включает в себя контейнер с хранилищем postgres, MQTT-брокер Mosquitto, сам шлюз gateway и web-приложение.

Запуск:

```bash
git clone https://github.com/TheTangerineOwl/iot-gateway.git
cd iot-gateway
cp .env.docker.example .env.docker  # отредактировать переменные при необходимости
docker-compose up -d
```

Проверка статуса адаптеров:

```bash
curl http://localhost:8081/api/v1/health
curl http://localhost:8082/api/v1/ws/health
```

Проверить статус docker-compose:

```bash
docker-compose ps
```

Остановка:

```bash
docker-compose down
```

Остановка с удалением данных (данные хранилища-контейнера postgres будут потеряны):

```bash
docker-compose down -v
```

## Конфигурация

Пример конфигурации расположен в `.env.example`, для запуска через Docker - в `.env.docker.example`.  
`.env.testing.example` предоставляет пример конфигурации для тестов.

Конфигурация может задаваться через YAML и через .env (вторая приоритетнее).

Подробнее про YAML-конфигурацию и вообще синтаксис конфигурации - в [config/README.md](config/README.md)

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

Логи генерируются в `logs/` (или другой директории, заданной в `.env` через `GATEWAY__LOGGER__DIR`) с названием в формате `ГГГГ-ММ-ДД_чч-мм-сс` при каждом запуске шлюза.

### Формат логов
```log
%(asctime)s │ %(levelname)-7s │ %(name)-30s │ %(message)s
```
Пример:
```log
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

## Добавление новых функций

### Добавление нового адаптера
1. Создать файл в `protocols/adapters/your_adapter.py`
2. Наследоваться от базового класса адаптера
3. Реализовать абстрактные методы
4. Добавить конфигурацию
5. Зарегистрировать в `Gateway`
### Добавление нового этапа Pipeline
1. Создать класс в `core/pipeline/stages.py`
2. Наследоваться от `PipelineStage`
3. Реализовать метод `async def process(self, message: Message) -> Message`
4. Зарегистрировать в `Gateway`

## :handshake: Вклад в проект
1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменений (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request
## 📄 Лицензия
будет добавлена позже  
(кто в здравом уме захочет этим пользоваться)
## Контакты  
---
GitHub: :call_me_hand:[@TheTangerineOwl](https://github.com/TheTangerineOwl)  
Project Link: [https://github.com/TheTangerineOwl/iot-gateway](https://github.com/TheTangerineOwl/iot-gateway)  
**Последнее обновление**: 26.04.2026  
**Версия**: 0.6.0+
---