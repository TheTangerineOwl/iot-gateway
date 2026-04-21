#!/bin/bash
# Скрипт для рекурсивной чистки директории с логами.

PATTERN="*.log"
DEFAULT_DIR=${GATEWAY__LOGGER__DIR:-"logs/"}
DIR=${1:-$DEFAULT_DIR}

echo "Внимание! Будут удалены следующие файлы по шаблону $PATTERN в $DIR"

find "$DIR" -type f -name "$PATTERN" -print

read -p "Продолжить? (y/n): " confirm

if [ "$confirm" != "${confirm#[Yy]}" ] ; then

    echo "Начинаем удаление..."
    find "$DIR" -type f -name "$PATTERN" -delete

    if [ $? -eq 0 ]; then
    echo "Удаление завершено успешно."
    else
    echo "Ошибка при удалении файлов."
    fi

else
    exit;
fi
