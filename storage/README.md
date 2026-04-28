# Хранилище данных

Шлюз поддерживает два хранилища: **SQLite** (для локальной разработки) и **PostgreSQL** (для production). Активное хранилище выбирается через `GATEWAY__GENERAL__STORAGE_TYPE=sqlite|postgresql`.

Оба реализуют интерфейс `StorageBase` (`storage/base.py`) с идентичным набором методов. Подписчик шины `StorageSubscriber` (`storage/subscriber.py`) слушает топик обработанной телеметрии и сохраняет записи через `storage.save()`.

---

## Схема базы данных

### Таблица `telemetry`

Хранит записи телеметрии от устройств.

| Столбец | Тип (SQLite / PG) | Описание |
|---|---|---|
| `id` | `INTEGER AUTOINCREMENT` / `BIGSERIAL` | Первичный ключ |
| `message_id` | `TEXT NOT NULL` | UUID сообщения |
| `device_id` | `TEXT NOT NULL` | Идентификатор устройства |
| `protocol` | `TEXT DEFAULT ''` | Протокол (`http`, `websocket`, `coap`, `mqtt`) |
| `payload` | `TEXT NOT NULL` | JSON-строка с данными телеметрии |
| `timestamp` | `REAL` / `DOUBLE PRECISION` | Unix-время (секунды с эпохи UTC) |

**Индексы:**
- `idx_device_id` — по `device_id` (быстрый поиск по устройству)
- `idx_timestamp` — по `timestamp` (сортировка по времени)

### Таблица `devices`

Реестр известных устройств, синхронизируется с in-memory реестром шлюза.

| Столбец | Тип (SQLite / PG) | Описание |
|---|---|---|
| `device_id` | `TEXT PRIMARY KEY` | Идентификатор устройства |
| `name` | `TEXT NOT NULL DEFAULT ''` | Имя устройства |
| `device_type` | `TEXT NOT NULL DEFAULT 'unknown'` | Тип устройства |
| `device_status` | `TEXT NOT NULL DEFAULT 'offline'` | Статус (`online`, `offline`) |
| `protocol` | `TEXT NOT NULL DEFAULT 'Unknown'` | Последний протокол подключения |
| `last_response` | `REAL` / `DOUBLE PRECISION NOT NULL DEFAULT 0.0` | Unix-время последней активности |
| `created_at` | `REAL` / `DOUBLE PRECISION NOT NULL DEFAULT 0.0` | Unix-время первой регистрации |

### Таблица `users` *(только в веб-приложении)*

Создаётся бэкендом веб-приложения через SQLAlchemy. Хранит пользователей веб-интерфейса. Подробнее — в `web/README.md`.

---

## SQL-запросы

### Вставка телеметрии

**SQLite:**
```sql
INSERT INTO telemetry (message_id, device_id, protocol, payload, timestamp)
VALUES (?, ?, ?, ?, ?);
```

**PostgreSQL:**
```sql
INSERT INTO telemetry (message_id, device_id, protocol, payload, timestamp)
VALUES (%s, %s, %s, %s, %s);
```

### Получение последних записей устройства

```sql
SELECT message_id, device_id, protocol, payload, timestamp
FROM telemetry
WHERE device_id = ?          -- %s для PostgreSQL
ORDER BY timestamp DESC
LIMIT ?;
```

### Upsert устройства

**SQLite:**
```sql
INSERT INTO devices (device_id, name, device_type, device_status, protocol, last_response, created_at)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(device_id) DO UPDATE SET
    name          = excluded.name,
    device_type   = excluded.device_type,
    device_status = excluded.device_status,
    protocol      = excluded.protocol,
    last_response = excluded.last_response;
```

**PostgreSQL:**
```sql
INSERT INTO devices (device_id, name, device_type, device_status, protocol, last_response, created_at)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT(device_id) DO UPDATE SET
    name          = EXCLUDED.name,
    device_type   = EXCLUDED.device_type,
    device_status = EXCLUDED.device_status,
    protocol      = EXCLUDED.protocol,
    last_response = EXCLUDED.last_response;
```

> Поле `created_at` при обновлении **не** перезаписывается — сохраняется время первой регистрации устройства.

### Удаление устройства

```sql
DELETE FROM devices WHERE device_id = ?;   -- %s для PostgreSQL
```

### Загрузка всех устройств

```sql
SELECT device_id, name, device_type, device_status, protocol, last_response, created_at
FROM devices;
```

---

## Конфигурация

### SQLite

**YAML** (`config/configuration/storage/sqlite/default.yaml`):
```yaml
dbpath: data/telemetry.db
```

**.env:**
```env
GATEWAY__GENERAL__STORAGE_TYPE=sqlite
STORAGE__SQLITE__DBPATH=data/telemetry.db
```

Директория для файла БД создаётся автоматически при старте. Рекомендуется монтировать папку `data/` как volume при работе в Docker.

### PostgreSQL

**.env:**
```env
GATEWAY__GENERAL__STORAGE_TYPE=postgresql
STORAGE__POSTGRESQL__USER__USERNAME=admin
STORAGE__POSTGRESQL__USER__PASSWORD=password
STORAGE__POSTGRESQL__ADDRESS__HOST=localhost
STORAGE__POSTGRESQL__ADDRESS__PORT=5432
STORAGE__POSTGRESQL__DBNAME=iotgateway
STORAGE__POSTGRESQL__APP_NAME=gateway
```

В `docker-compose.yml` строка подключения формируется автоматически из этих переменных.

---

## Жизненный цикл

1. При запуске шлюза вызывается `storage.setup()` — создаётся соединение и таблицы (если не существуют).
2. `StorageSubscriber` подписывается на топик `gateway/processed/telemetry/+` и при каждом сообщении вызывает `storage.save()`.
3. При регистрации или смене статуса устройства вызывается `storage.upsert_device()`.
4. При удалении устройства из реестра (таймаут) вызывается `storage.delete_device()`.
5. При старте шлюза устройства восстанавливаются из БД через `storage.load_devices()`.
6. При штатной остановке вызывается `storage.teardown()` — соединение закрывается.
