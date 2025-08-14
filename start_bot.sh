#!/bin/bash

# Скрипт для запуска бота с правильным виртуальным окружением
cd "$(dirname "$0")"

echo "🤖 Запуск Tres Dias Israel Telegram Bot..."
echo "📁 Рабочая директория: $(pwd)"
echo "🐍 Python: $(./venv/bin/python --version)"
echo ""

# Запуск с правильным Python интерпретатором
./venv/bin/python main.py
