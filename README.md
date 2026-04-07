# IoT-шлюз на Python

IoT-шлюз на Python, предназначенный для запуска на одноплатном устройстве. Принимает телеметрию от устройств, обрабатывает ее через конвейер этапов обработки и сохраняет в базе данных.

На данный момент (7.04.2026) шлюз взаимодействует только по HTTP-адаптеру и отправляет свои данные в поднятую SQLite базу и не имеет веб-приложения.

## Содержание

- [Быстрый старт](#быстрый-старт)
- [Конфигурация](#конфигурация)
- [Тестирование](#тестирование)
- [Логирование](#логирование)

## Быстрый старт

### 1. Клонировать и установить зависимости

```bash
git clone https://github.com/TheTangerineOwl/iot-gateway.git

cd iot-gateway

python -m venv venv

# Linux / macOS

source venv/bin/activate

# Windows

venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Настроить окружение

```bash
cp env.example .env
# при необходимости отредактировать переменные окружения
```

### 3. Директории для логов

```bash
mkdir -p data logs/ logs/sim
```

### 4. Запуск

```bash
python main.py
```

На данный момент шлюз поднимает HTTP-сервер на `0.0.0.0:8081` (по умолчанию) и общается только по нему. Это будет доработано.

### 5*. Запустить симулятор в отдельной консоли

Просмотр параметров симуляции:

```bash
python run_sim.py --help
```

Запуск:

```bash
python run_sim.py
```

Симулятор создает тестовые устройства, регистрирует их на шлюзе и отправляет телеметрию в соответствии с настройками.

## Конфигурация

Пример настройки переменных окружения лежит в `env.example`.

## Тестирование

```bash
pip install pytest pytest-asyncio

# все тесты
pytest

# юнит-тесты
pytest tests/unit/ -m unit

# интеграционные
pytest tests/integration -m integration

# конкретный модуль
pytest tests/unit/test_registry.py -v

```

## Логирование

`logs/gateway/` - логи шлюза (основной лог)

`logs/sim/` - логи симулятора

Формат: `%(asctime)s │ %(levelname)-7s │ %(name)-30s │ %(message)s`

`2026-04-07 12:00:00 │ INFO    │ core.gateway                   │ Starting gateway`
