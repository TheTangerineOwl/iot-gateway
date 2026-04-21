#!/bin/bash
# Скрипт для копирования шаблона заполнения .env в другой файл.
# ВНИМАНИЕ! При копировании файл будет заменен, не использовать
# в продакшене и там, где уже был файл с реальными значениями!

example=${1:-".env.example"}
env_name=${2:-".env"}

if [ ! -f "$example" ] ; then
    echo "Файл $example не найден"
    exit 1
fi

if [ ! -f "$env_name" ] ; then
    echo "!!!!!Файл $env_name будет перезаписан!!!!!"
fi

echo "Внимание! Содержимое $example будет скопировано в $env_name."

read -p "Продолжить? (y/n): " confirm

if [ "$confirm" != "${confirm#[Yy]}" ] ; then

    echo "Начинаем копирование..."
    cp $example $env_name

    if [ $? -eq 0 ]; then
    echo "Файл $example успешно скопирован в $env_name."
    else
    echo "Ошибка при копировании файлов."
    fi

else
    exit;
fi
