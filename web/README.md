# Web-интерфейс IoT Gateway

Веб-интерфейс для мониторинга и управления IoT Gateway.  
Состоит из FastAPI-бэкенда и React-фронтенда, раздаётся единым процессом на порту `8090`.

## Структура

<details>

<summary>Структура веб-приложения</summary>

```
frontend/                 # Фронтенд
Dockerfile
requirements.txt          # требования веб-приложения
backend/
├── main.py               # Точка входа FastAPI-приложения
├── dependencies/
│   ├── auth.py           # JWT-аутентификация (get_current_user)
│   ├── config.py         # Настройки через pydantic-settings (Settings)
│   └── database.py       # SQLAlchemy engine, сессии, инициализация БД
├── models/
│   └── user.py           # ORM-модель пользователя
├── routers/
│   ├── auth.py           # /web/api/auth/*
│   ├── devices.py        # /web/api/devices/*
│   ├── gateway.py        # /web/api/gateway/*
│   └── logs.py           # /web/api/logs/*
├── schemas/
│   ├── auth.py           # TokenResponse, LoginUserMe
│   ├── devices.py        # Device, DeviceList, Telemetry, CommandRequest/Response
│   ├── logs.py           # LogFileList, LogLines
│   └── gateway/
│       ├── status.py     # GatewayStatus и статусы адаптеров
│       └── config.py     # GatewayConfig и конфиги адаптеров
└── services/
    ├── auth.py           # JWT-токены, хэширование паролей
    ├── user_service.py   # Аутентификация пользователя через БД
    ├── gateway.py        # Получение статуса и конфигурации шлюза
    ├── devices.py        # Получение устройств и телеметрии, отправка команд
    └── logs.py           # Чтение лог-файлов, SSE-стрим
```

</details>

## Быстрый старт

### 1. Зависимости бэкенда

```bash
pip install -r requirements.txt   # из корня проекта
```

Либо установить отдельно: `fastapi`, `uvicorn`, `sqlalchemy[asyncio]`, `aiosqlite`, `asyncpg`, `pydantic-settings`, `python-jose[cryptography]`, `passlib[bcrypt]`, `aiohttp`.

### 2. Сборка фронтенда

```bash
cd web/frontend
npm install
npm run build
# собранные файлы появятся в web/static/
```

### 3. Переменные окружения

```env
WEB__SECRET_KEY=changeme-in-prod
WEB__ADMIN_USER=admin
WEB__ADMIN_PASSWORD=changeme
WEB__TOKEN_EXPIRE_MINUTES=60
WEB__GATEWAY_MANAGEMENT_URL=http://localhost:8001
WEB__LOGS_DIR=logs/
WEB__SQLITE_DBPATH=data/telemetry.db
WEB__HOST=0.0.0.0
WEB__PORT=8090
```

Все переменные читаются с префиксом `WEB__`. Разделитель вложенности — `__`.

### 4. Запуск

```bash
uvicorn web.backend.main:app --host 0.0.0.0 --port 8090
```

Интерфейс: `http://localhost:8090`  
Swagger UI: `http://localhost:8090/docs`

## API

Все защищённые эндпоинты требуют заголовок:
```
Authorization: Bearer <token>
```

Токен получается через `POST /web/api/auth/login`.

### Авторизация (`/web/api/auth`)

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/login` | Получить JWT-токен (form-data: `username`, `password`) |
| `POST` | `/logout` | Stateless-выход (клиент удаляет токен) |
| `GET` | `/me` | Информация о текущем пользователе |

### Шлюз (`/web/api/gateway`)

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/status` | Статус шлюза: адаптеры, реестр, шина сообщений, pipeline |
| `GET` | `/config` | Базовая конфигурация шлюза и адаптеров |

Данные получаются с management-адаптера шлюза (`WEB__GATEWAY_MANAGEMENT_URL`).

### Устройства (`/web/api/devices`)

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/` | Список всех устройств из реестра шлюза |
| `GET` | `/{device_id}` | Детали устройства + последняя телеметрия (`?limit=20`) |
| `POST` | `/{device_id}/command` | Отправить команду устройству через management-адаптер |

### Логи (`/web/api/logs`)

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/list` | Список лог-файлов из `WEB__LOGS_DIR` |
| `GET` | `/{filename}` | Содержимое файла (`?lines=100&level=INFO&search=текст`) |
| `GET` | `/stream` | SSE live-стрим активного лога (`?level=INFO`) |

## База данных

Бэкенд подключается к той же БД, что и основной шлюз, для чтения телеметрии.  
Дополнительно создаётся таблица `users` для хранения пользователей веб-интерфейса.

При старте автоматически создаётся пользователь-админ из `WEB__ADMIN_USER` / `WEB__ADMIN_PASSWORD`.
Эта настройка реализована только для разработки!!! В продакшене рекомендуется отключить создание админа от греха подальше и создавать их в БД вручную.

## Конфигурация

Все параметры читаются из переменных окружения с префиксом `WEB__`:

| Переменная | По умолчанию | Описание |
|---|---|---|
| `WEB__SECRET_KEY` | `changeme-in-prod` | Секрет для подписи JWT |
| `WEB__ADMIN_USER` | `admin` | Логин администратора |
| `WEB__ADMIN_PASSWORD` | `changeme` | Пароль администратора |
| `WEB__TOKEN_EXPIRE_MINUTES` | `60` | Время жизни токена (мин) |
| `WEB__GATEWAY_MANAGEMENT_URL` | `http://localhost:8001` | URL management-адаптера шлюза |
| `WEB__LOGS_DIR` | `logs/` | Директория лог-файлов шлюза |
| `WEB__SQLITE_DBPATH` | `data/telemetry.db` | Путь к SQLite БД |
| `WEB__HOST` | `0.0.0.0` | Хост для uvicorn |
| `WEB__PORT` | `8090` | Порт для uvicorn |
| `WEB__CHECK_TIMEOUT` | `5.0` | Таймаут запросов к шлюзу (сек) |
| `WEB__CORS_ORIGINS` | `*` | Разрешённые CORS-источники (через запятую) |

## Фронтенд

После `npm run build` (в `web/frontend/`) собранные файлы попадают в `web/static/`.  
Бэкенд монтирует `/assets` как статику и отдаёт `index.html` на все остальные пути (SPA fallback).  
Если фронтенд не собран — `GET /` вернёт `503` с подсказкой.
