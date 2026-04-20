#!/bin/bash
# Скрипт для удаления кастомных используемых конфигов.

PATTERN=("default.yaml" "running.yaml")

DEFAULT_DIR="config/configuration/"
DIR=${1:-$DEFAULT_DIR}

echo "Внимание! Будут удалены следующие файлы в $DIR: "

for p in ${PATTERN[@]}; do
    find "$DIR" -type f -name "$p" -print
done

read -p "Продолжить? (y/n): " confirm

if [ "$confirm" != "${confirm#[Yy]}" ] ; then

    echo "Начинаем удаление..."
    for p in ${PATTERN[@]}; do
        find "$DIR" -type f -name "$p" -delete

        if [ $? -eq 0 ]; then
        echo "Удаление $p для завершено успешно."
        else
        echo "Ошибка при удалении файлов для $p."
        fi
    done

else
    exit;
fi

