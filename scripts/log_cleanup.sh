#!/bin/bash
# Скрипт для архивирования старых логов

LOG_DIR="logs"
ARCHIVE_DIR="logs/archive"
DAYS_TO_KEEP=30

echo "🗂️ Архивирование логов старше $DAYS_TO_KEEP дней..."

# Создаем папку архива
mkdir -p "$ARCHIVE_DIR"

# Находим и архивируем старые логи
find "$LOG_DIR" -name "*.log.*" -mtime +$DAYS_TO_KEEP -type f | while read file; do
    echo "📦 Архивируем: $file"
    mv "$file" "$ARCHIVE_DIR/"
done

# Сжимаем архивные файлы
find "$ARCHIVE_DIR" -name "*.log.*" -not -name "*.gz" -type f | while read file; do
    echo "🗜️ Сжимаем: $file"
    gzip "$file"
done

echo "✅ Архивирование завершено"

