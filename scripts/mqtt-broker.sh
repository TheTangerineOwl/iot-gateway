#!/bin/bash
# Скрипт для управления Docker-контейнером с Mosquitto MQTT брокером
# 
# ./scripts/mqtt-broker.sh start  # Запустить Mosquitto брокер
# ./scripts/mqtt-broker.sh stop  # Остановить брокер
# ./scripts/mqtt-broker.sh restart  # Перезагрузить брокер
# ./scripts/mqtt-broker.sh logs  # Просмотреть логи
# ./scripts/mqtt-broker.sh shell  # Открыть shell контейнера
# ./scripts/mqtt-broker.sh remove  # Удалить контейнер

set -e

# Конфигурация
CONTAINER_NAME="iot-gateway-mosquitto"
IMAGE="eclipse-mosquitto:latest"
MQTT_PORT="${MQTT_PORT:-1883}"
MQTT_WS_PORT="${MQTT_WS_PORT:-9001}"
BROKER_DATA_DIR="${BROKER_DATA_DIR:-./data/mosquitto}"

# Проверка Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "Docker не установлен. Пожалуйста, установите Docker для продолжения."
        exit 1
    fi
    
    if ! docker ps &> /dev/null; then
        echo -e "Docker демон не запущен. Пожалуйста, запустите Docker."
        exit 1
    fi
}

# Функция для запуска брокера
start_broker() {
    echo -e "Запуск Mosquitto MQTT брокера..."
    
    # Создание директории для данных
    mkdir -p "$BROKER_DATA_DIR"
    
    # Проверка, запущен ли уже контейнер
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "Контейнер $CONTAINER_NAME уже запущен"
        return 0
    fi
    
    # Проверка, существует ли остановленный контейнер
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "Запуск существующего контейнера..."
        docker start "$CONTAINER_NAME"
    else
        echo -e "Создание нового контейнера..."
        docker run -d \
            --name "$CONTAINER_NAME" \
            -p "${MQTT_PORT}:1883" \
            -p "${MQTT_WS_PORT}:9001" \
            -v "$BROKER_DATA_DIR:/mosquitto/data" \
            -v "$BROKER_DATA_DIR/config:/mosquitto/config" \
            -v "$BROKER_DATA_DIR/log:/mosquitto/log" \
            "$IMAGE"
    fi
    
    # Ожидание готовности брокера
    echo -e "Ожидание запуска брокера..."
    sleep 2
    
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "Mosquitto MQTT брокер запущен"
        echo -e "MQTT порт: $MQTT_PORT"
        echo -e "WebSocket порт: $MQTT_WS_PORT"
        echo -e "Данные сохраняются в: $BROKER_DATA_DIR"
    else
        echo -e "Ошибка при запуске брокера"
        exit 1
    fi
}

# Функция для остановки брокера
stop_broker() {
    echo -e "Остановка Mosquitto MQTT брокера..."
    
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "Контейнер $CONTAINER_NAME не запущен"
        return 0
    fi
    
    docker stop "$CONTAINER_NAME"
    echo -e "Mosquitto MQTT брокер остановлен"
}

# Функция для перезагрузки брокера
restart_broker() {
    echo -e "Перезагрузка Mosquitto MQTT брокера..."
    stop_broker
    sleep 1
    start_broker
    echo -e "Mosquitto MQTT брокер перезагружен"
}

# Функция для просмотра логов
show_logs() {
    echo -e "Логи Mosquitto MQTT брокера:"
    docker logs -f "$CONTAINER_NAME" 2>/dev/null || echo -e "Контейнер $CONTAINER_NAME не запущен"
}

# Функция для открытия shell контейнера
open_shell() {
    echo -e "Открытие shell контейнера..."
    docker exec -it "$CONTAINER_NAME" sh
}

# Функция для удаления контейнера
remove_container() {
    echo -e "Удаление контейнера $CONTAINER_NAME..."
    
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "Остановка контейнера перед удалением..."
        docker stop "$CONTAINER_NAME"
    fi
    
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        docker rm "$CONTAINER_NAME"
        echo -e "Контейнер удален"
    else
        echo -e "Контейнер не найден"
    fi
}

# Функция для показа информации о брокере
show_status() {
    echo -e "Статус Mosquitto MQTT брокера:"
    
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "Статус: ЗАПУЩЕН"
        
        # Информация о портах
        echo ""
        echo -e "Информация о подключении:"
        echo "  MQTT:      localhost:$MQTT_PORT"
        echo "  WebSocket: localhost:$MQTT_WS_PORT"
        echo ""
        
        # Детали контейнера
        docker ps --filter "name=${CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    else
        echo -e "Статус: ОСТАНОВЛЕН"
    fi
}

# Функция для тестирования подключения
test_connection() {
    echo -e "Тестирование подключения к MQTT брокеру..."
    
    if ! docker exec "$CONTAINER_NAME" mosquitto_sub -h localhost -t '$SYS/#' -C 1 &> /dev/null; then
        echo -e "Не удается подключиться к брокеру"
        exit 1
    fi
    
    echo -e "Подключение успешно"
}

# Функция помощи
show_help() {
    echo "Управление Mosquitto MQTT брокером"
    echo ""
    echo "Использование: $0 <команда> [опции]"
    echo ""
    echo "Команды:"
    echo "  start       Запустить Mosquitto брокер"
    echo "  stop        Остановить брокер"
    echo "  restart     Перезагрузить брокер"
    echo "  status      Показать статус брокера"
    echo "  logs        Просмотреть логи (Ctrl+C для выхода)"
    echo "  shell       Открыть shell контейнера"
    echo "  test        Протестировать подключение"
    echo "  remove      Удалить контейнер (не удаляет данные)"
    echo "  help        Показать эту справку"
    echo ""
    echo "Переменные окружения:"
    echo "  MQTT_PORT              MQTT порт (по умолчанию: 1883)"
    echo "  MQTT_WS_PORT           WebSocket порт (по умолчанию: 9001)"
    echo "  BROKER_DATA_DIR        Директория данных брокера (по умолчанию: ./data/mosquitto)"
    echo ""
    echo "Примеры:"
    echo "  # Запустить брокер на нестандартном порту"
    echo "  MQTT_PORT=1884 $0 start"
    echo ""
    echo "  # Просмотреть логи"
    echo "  $0 logs"
    echo ""
    echo "  # Протестировать подключение"
    echo "  $0 test"
}

# Основная логика
main() {
    check_docker
    
    case "${1:-help}" in
        start)
            start_broker
            ;;
        stop)
            stop_broker
            ;;
        restart)
            restart_broker
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        shell)
            open_shell
            ;;
        test)
            test_connection
            ;;
        remove)
            remove_container
            ;;
        help)
            show_help
            ;;
        *)
            echo -e "Неизвестная команда: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
